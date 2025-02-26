import datetime
import logging
import math
import os
from abc import ABC, abstractmethod
from enum import StrEnum, Enum
from pathlib import Path
from typing import Tuple, Set

import numpy as np
from sentinelhub import (
    CRS,
    BBox,
    DataCollection,
    DownloadFailedException,
    MimeType,
    SentinelHubRequest,
    bbox_to_dimensions,
    SHConfig,
    ServiceUrl,
)
from sentinelhub.download.models import DownloadResponse

from naturalness.exception import OperatorInteractionException, OperatorValidationException

log = logging.getLogger(__name__)


class OutputFormat(Enum):
    BIT_8 = '8 bit TIFF/JPG/PNG'
    BIT_16 = '16 bit TIFF/JPG/PNG'
    BIT_32 = '32 bit TIFF/JPG/PNG'
    OCTET_STREAM = 'OCTET STREAM'


class Index(StrEnum):
    NDVI = 'NDVI'
    WATER = 'WATER'
    NATURALNESS = 'NATURALNESS'


class ImageryStore(ABC):
    @abstractmethod
    def imagery(
        self,
        index: Index,
        bbox: Tuple[float, float, float, float],
        start_date: str,
        end_date: str,
        resolution: int = 10,
    ) -> Tuple[np.ndarray, Tuple[int, int]]:
        """Returns images as numpy array in shape [height, width, channels]"""
        pass


class SentinelHubOperator(ImageryStore):
    def __init__(
        self,
        api_id: str,
        api_secret: str,
        script_path: Path,
        cache_dir: Path,
    ):
        self.config = SHConfig(**{'sh_client_id': api_id, 'sh_client_secret': api_secret})
        self.evalscripts = {index: (script_path / f'{index}.js').read_text() for index in Index}

        self.data_folder = cache_dir
        self.data_folder.mkdir(parents=True, exist_ok=True)
        self.MAX_REVISIT_RATE = 1 / 5

    def imagery(
        self,
        index: Index,
        bbox: Tuple[float, float, float, float],
        start_date: str,
        end_date: str,
        resolution: int = 10,
    ) -> tuple[np.ndarray, tuple[int, int]]:
        bbox = BBox(bbox=bbox, crs=CRS.WGS84)
        bbox_width, bbox_height = bbox_to_dimensions(bbox, resolution=resolution)

        if bbox_width > 2500 or bbox_height > 2500:
            raise OperatorValidationException('Area exceeds processing limit: 2500 px x 2500 px')

        request = SentinelHubRequest(
            data_folder=str(self.data_folder),
            evalscript=self.evalscripts[index],
            input_data=[
                SentinelHubRequest.input_data(
                    data_collection=DataCollection.SENTINEL2_L2A,
                    identifier='s2',
                    time_interval=(start_date, end_date),
                ),
            ],
            responses=[
                SentinelHubRequest.output_response(index, MimeType.TIFF),
            ],
            bbox=bbox,
            size=(bbox_width, bbox_height),
            config=self.config,
        )
        min_estimated_pus, max_estimated_pus = self.estimate_pus(
            index=index,
            request=request,
        )
        try:
            data = request.get_data(save_data=True, decode_data=False)[0]
        except DownloadFailedException:
            log.exception('Download of remote sensing scenes failed')
            raise OperatorInteractionException('SentinelHub operator interaction not possible.')

        _ = self._get_actual_pus(
            data=data,
            min_estimated_pus=min_estimated_pus,
            max_estimated_pus=max_estimated_pus,
        )

        return data.decode(), (bbox_height, bbox_width)

    def estimate_pus(
        self,
        index: Index,
        request: SentinelHubRequest,
        eval_duration_range: Tuple[int, int] = (1100, 1300),
    ) -> Tuple[float, float]:
        lower_eval_duration_bound, upper_eval_duration_bound = eval_duration_range
        assert lower_eval_duration_bound <= upper_eval_duration_bound, (
            'The eval script execution range is given in ' 'the wrong order, provide the lower bound ' 'first.'
        )

        _, response_path = request.download_list[0].get_storage_paths()
        if os.path.exists(response_path):
            log.debug('Expecting a cached result with no PU consumption.')
            return 0.0, 0.0

        match index:
            case Index.NDVI:
                band_number = 2
            case Index.WATER:
                band_number = 1
            case Index.NATURALNESS:
                band_number = 3
            case _:
                raise ValueError(f'Index {index} is not supported for PU estimation')

        output_format = OutputFormat.BIT_8

        request_input = request.payload.get('input')
        request_output = request.payload.get('output')

        service_urls = set(service.service_url for service in request_input.get('data'))
        local_collections = set(filter(lambda url: url == ServiceUrl.MAIN, service_urls))
        remote_collections = service_urls.difference(local_collections)

        bbox_height = request_output.get('height')
        bbox_width = request_output.get('width')

        start_date = request_input.get('data')[0].get('dataFilter').get('timeRange').get('from')
        start_date = datetime.datetime.fromisoformat(start_date).date()
        end_date = request_input.get('data')[0].get('dataFilter').get('timeRange').get('to')
        end_date = datetime.datetime.fromisoformat(end_date).date()
        n_samples = math.ceil((end_date - start_date).days * self.MAX_REVISIT_RATE)

        pu_range = [
            SentinelHubOperator._calculate_pus(
                width=bbox_width,
                height=bbox_height,
                band_number=band_number,
                output_format=output_format,
                local_collections=local_collections,
                remote_collections=remote_collections,
                eval_script_duration=eval_duration,
                n_samples=n_samples,
            )
            for eval_duration in (lower_eval_duration_bound, upper_eval_duration_bound)
        ]

        min_pu, max_pu = pu_range
        log.info(f'Estimated PU consumed by request lie between: {min_pu} and {max_pu}')
        return min_pu, max_pu

    @staticmethod
    def _calculate_pus(
        *,
        width: int,
        height: int,
        band_number: int,
        output_format: OutputFormat,
        n_samples: int,
        local_collections: Set[str],
        remote_collections: Set[str],
        eval_script_duration: int,
    ) -> float:
        aoi_factor = max((width * height) / (512 * 512), 0.01)

        band_factor = band_number / 3.0

        match output_format:
            case OutputFormat.BIT_8:
                output_format_factor = 1.0
            case OutputFormat.BIT_16:
                output_format_factor = 1.0
            case OutputFormat.BIT_32:
                output_format_factor = 2.0
            case OutputFormat.OCTET_STREAM:
                output_format_factor = 1.4
            case _:
                raise ValueError(f'Output format {output_format} is not supported for PU calculation')

        data_samples_factor = n_samples

        data_fusion_factor = len(local_collections) + 2 * len(remote_collections)

        if eval_script_duration > 200:
            eval_factor = 1.0 + math.ceil((eval_script_duration - 200) / 100) * 0.5
        else:
            eval_factor = 1.0

        return math.prod(
            (aoi_factor, band_factor, output_format_factor, data_samples_factor, data_fusion_factor, eval_factor)
        )

    @staticmethod
    def _get_actual_pus(data: DownloadResponse, min_estimated_pus: float, max_estimated_pus: float) -> float:
        actual_pus = (
            0.0 if min_estimated_pus == max_estimated_pus == 0.0 else float(data.headers['x-processingunits-spent'])
        )
        logging.debug(f'The request required {actual_pus} PUs')
        if actual_pus > 0.0 and not min_estimated_pus <= actual_pus <= max_estimated_pus:
            log.warning(
                f'The pu estimation was inaccurate. The request required {actual_pus} PUs but the estimated range '
                f'was {min_estimated_pus}..{max_estimated_pus} PUs.'
            )

        return actual_pus

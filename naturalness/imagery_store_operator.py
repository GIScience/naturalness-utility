import logging
import math
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
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
    ResamplingType,
)
from sentinelhub.api.catalog import get_available_timestamps
from sentinelhub.download.models import DownloadResponse

from naturalness.exception import OperatorInteractionException, OperatorValidationException

log = logging.getLogger(__name__)


@dataclass
class ProcessingUnitStats:
    estimated: float
    consumed: float


@dataclass
class RemoteSensingResult:
    index_data: np.ndarray
    height: int
    width: int
    bbox: Tuple[float, float, float, float]
    pus: ProcessingUnitStats


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
        resolution: int = 90,
    ) -> RemoteSensingResult:
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

    def imagery(
        self,
        index: Index,
        bbox: Tuple[float, float, float, float],
        start_date: str,
        end_date: str,
        resolution: int = 90,
    ) -> RemoteSensingResult:
        bbox_obj = BBox(bbox=bbox, crs=CRS.WGS84)
        bbox_width, bbox_height = bbox_to_dimensions(bbox_obj, resolution=resolution)

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
                    downsampling=ResamplingType.BICUBIC,
                ),
            ],
            responses=[
                SentinelHubRequest.output_response(index, MimeType.TIFF),
            ],
            bbox=bbox_obj,
            size=(bbox_width, bbox_height),
            config=self.config,
        )
        pu_stats = self.estimate_pus(index=index, request=request)
        try:
            data = request.get_data(save_data=True, decode_data=False)[0]
        except DownloadFailedException:
            log.exception('Download of remote sensing scenes failed')
            raise OperatorInteractionException('SentinelHub operator interaction not possible.')

        pu_stats.consumed = self._get_actual_pus(data=data)

        if pu_stats.consumed > 0.0 and not math.isclose(pu_stats.estimated, pu_stats.consumed):
            log.warning(
                f'The pu estimation was inaccurate. The request required {pu_stats.estimated} PUs but the estimation was '
                f'{pu_stats.consumed} PUs.'
            )

        data_cleaned = data.decode()
        match index:
            case 'NDVI':
                divisor = 2**16 / 2 - 1
            case 'NATURALNESS':
                divisor = 2**16 - 1
            case _:
                divisor = 1
        data_cleaned = data_cleaned / divisor

        log.info('RS data retrieved')
        return RemoteSensingResult(
            index_data=data_cleaned,
            height=bbox_height,
            width=bbox_width,
            bbox=bbox,
            pus=pu_stats,
        )

    def estimate_pus(self, index: Index, request: SentinelHubRequest) -> ProcessingUnitStats:
        _, response_path = request.download_list[0].get_storage_paths()
        if os.path.exists(response_path):
            log.debug('Expecting a cached result with no PU consumption.')
            return ProcessingUnitStats(estimated=0.0, consumed=math.nan)

        match index:
            case Index.NDVI:
                band_number = 3
                output_format = OutputFormat.BIT_16
            case Index.WATER:
                band_number = 1
                output_format = OutputFormat.BIT_8
            case Index.NATURALNESS:
                band_number = 3
                output_format = OutputFormat.BIT_16
            case _:
                raise ValueError(f'Index {index} is not supported for PU estimation')

        request_input = request.payload.get('input')
        request_output = request.payload.get('output')

        service_urls = set(service.service_url for service in request_input.get('data'))
        local_collections = set(filter(lambda url: url == ServiceUrl.MAIN, service_urls))
        remote_collections = service_urls.difference(local_collections)

        bbox_height = request_output.get('height')
        bbox_width = request_output.get('width')

        n_samples = len(
            get_available_timestamps(
                config=self.config,
                bbox=BBox(bbox=request_input.get('bounds').get('bbox'), crs=CRS.WGS84),
                time_interval=(
                    request_input.get('data')[0].get('dataFilter').get('timeRange').get('from'),
                    request_input.get('data')[0].get('dataFilter').get('timeRange').get('to'),
                ),
                data_collection=DataCollection.SENTINEL2_L2A,
            )
        )
        estimated_pus = SentinelHubOperator._calculate_pus(
            width=bbox_width,
            height=bbox_height,
            band_number=band_number,
            output_format=output_format,
            local_collections=local_collections,
            remote_collections=remote_collections,
            n_samples=n_samples,
        )

        log.info(f'Estimated PU consumed by request are {estimated_pus}')
        return ProcessingUnitStats(estimated=estimated_pus, consumed=math.nan)

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
        eval_script_duration: int = 200,
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

        if len(local_collections) > 1 or len(remote_collections) > 0:
            log.warning(
                'The estimation of PUs with remote collection or more than one collection seems to be imprecise.'
            )
        data_fusion_factor = len(local_collections) + 2 * len(remote_collections)

        eval_surcharge = max(eval_script_duration - 200, 0)
        eval_factor = 1.0 + math.ceil(eval_surcharge / 100) * 0.5

        computed_pu: float = math.prod(
            (aoi_factor, band_factor, output_format_factor, data_samples_factor, data_fusion_factor, eval_factor)
        )
        return max(computed_pu, 0.005)

    @staticmethod
    def _get_actual_pus(data: DownloadResponse) -> float:
        actual_pus = float(data.headers['x-processingunits-spent'])
        logging.debug(f'The request required {actual_pus} PUs')
        return actual_pus

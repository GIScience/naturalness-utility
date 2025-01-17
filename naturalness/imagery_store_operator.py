import logging
from abc import ABC, abstractmethod
from enum import StrEnum
from pathlib import Path
from typing import Tuple

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
)

from naturalness.exception import OperatorInteractionException, OperatorValidationException

log = logging.getLogger(__name__)


class Index(StrEnum):
    NDVI = 'NDVI'


class ImageryStore(ABC):
    @abstractmethod
    def imagery(
        self,
        index: Index,
        area_coords: Tuple[float, float, float, float],
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
        self.evalscripts = {index: (script_path / f'{index}_evalscript.js').read_text() for index in Index}

        self.data_folder = cache_dir
        self.data_folder.mkdir(parents=True, exist_ok=True)

    def imagery(
        self,
        index: Index,
        area_coords: Tuple[float, float, float, float],
        start_date: str,
        end_date: str,
        resolution: int = 10,
    ) -> tuple[np.ndarray, tuple[int, int]]:
        bbox = BBox(bbox=area_coords, crs=CRS.WGS84)
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
                SentinelHubRequest.output_response(f'{index}', MimeType.TIFF),
            ],
            bbox=bbox,
            size=(bbox_width, bbox_height),
            config=self.config,
        )
        try:
            return request.get_data(save_data=True)[0], (bbox_height, bbox_width)
        except DownloadFailedException:
            log.exception('Download of remote sensing scenes failed')
            raise OperatorInteractionException('SentinelHub operator interaction not possible.')

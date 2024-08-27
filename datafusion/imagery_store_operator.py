from pathlib import Path
import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, Tuple
from omegaconf import DictConfig
from sentinelhub import (
    CRS,
    BBox,
    DataCollection,
    DownloadFailedException,
    MimeType,
    SentinelHubRequest,
    SHConfig,
    bbox_to_dimensions,
)

from datafusion.exception import OperatorInteractionException, OperatorValidationException


class ImageryStore(ABC):
    @abstractmethod
    def imagery(
        self,
        area_coords: Tuple[float, float, float, float],
        start_date: str,
        end_date: str,
        resolution: int = 10,
        save_data: bool = False,
    ) -> Tuple[Dict[str, np.ndarray], Tuple[int, int]]:
        pass


class SentinelHubOperator(ImageryStore):
    def __init__(
        self,
        api_id: str,
        api_secret: str,
        evalscript_name: str,
        cache_dir: Path,
    ):
        self.config = SHConfig(**{'sh_client_id': api_id, 'sh_client_secret': api_secret})
        self.cache_dir: Path = cache_dir
        self.data_folder = self.cache_dir
        self.data_folder.mkdir(parents=True, exist_ok=True)

        self.evalscript = (Path('conf') / f'{evalscript_name}.js').read_text()

    def imagery(
        self,
        area_coords: Tuple[float, float, float, float],
        start_date: str,
        end_date: str,
        resolution: int = 10,
        save_data: bool = False,
    ) -> tuple[Dict[str, np.ndarray], tuple[int, int]]:
        """
        returns images as numpy array in shape [height, widht, channels]
        """
        bbox = BBox(bbox=area_coords, crs=CRS.WGS84)
        bbox_width, bbox_height = bbox_to_dimensions(bbox, resolution=resolution)

        if bbox_width > 2500 or bbox_height > 2500:
            raise OperatorValidationException('Area exceeds processing limit: 2500 px x 2500 px')

        request = SentinelHubRequest(
            data_folder=str(self.data_folder),
            evalscript=self.evalscript,
            input_data=[
                SentinelHubRequest.input_data(
                    data_collection=DataCollection.SENTINEL2_L2A,
                    identifier='s2',
                    time_interval=(start_date, end_date),
                ),
            ],
            responses=[
                SentinelHubRequest.output_response('indice', MimeType.TIFF),
            ],
            bbox=bbox,
            size=(bbox_width, bbox_height),
            config=self.config,
        )
        try:
            return request.get_data(save_data=save_data)[0], (bbox_height, bbox_width)
        except DownloadFailedException:
            print('Download failed')
            raise OperatorInteractionException('SentinelHub operator interaction not possible.')


def resolve_imagery_store(cfg: DictConfig, cache_dir: Path) -> ImageryStore:
    return SentinelHubOperator(
        cfg.api_id,
        cfg.api_secret,
        cfg.evalscript_name,
        cache_dir=cache_dir / 'imagery',
    )

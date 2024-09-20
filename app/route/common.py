import uuid
import logging
from datetime import date, datetime, timedelta
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple, Optional

import numpy as np
import geopandas as gpd
import rasterio as rio
from rasterio.crs import CRS
from rasterstats import zonal_stats
from pydantic import confloat, Field, BaseModel, model_validator
from starlette.requests import Request
from starlette.responses import FileResponse
from starlette.background import BackgroundTask

log = logging.getLogger(__name__)


class GeoTiffResponse(FileResponse):
    media_type = 'image/geotiff'


@dataclass
class RemoteSensingResult:
    index_data: np.ndarray
    height: int
    width: int
    area_coords: Tuple[float, float, float, float]


class DatafusionWorkUnit(BaseModel):
    """Datafusion area of interest."""

    area_coords: Tuple[
        confloat(ge=-180, le=180), confloat(ge=-90, le=90), confloat(ge=-180, le=180), confloat(ge=-90, le=90)
    ] = Field(
        title='Area Coordinates',
        description='Bounding box coordinates in WGS 84 (west, south, east, north)',
        examples=[[8.65, 49.38, 8.75, 49.41]],
    )
    start_date: Optional[date] = Field(
        title='Start Date',
        description='Lower bound (inclusive) of remote sensing imagery acquisition date (UTC). '
        'If not set it will be automatically set to one month (30 days) before `end_date`',
        examples=['2023-05-01'],
        default=None,
    )
    end_date: date = Field(
        title='End Date',
        description='Upper bound (inclusive) of remote sensing imagery acquisition date (UTC).'
        "Defaults to today's date",
        examples=['2023-06-01'],
        default=datetime.now().date(),
    )
    save_data: Optional[bool] = Field(
        title='Save Data',
        description='Save the data to disk [True, False]',
        examples=[True],
        default=False,
    )

    @model_validator(mode='after')
    def minus_week(self) -> 'DatafusionWorkUnit':
        if not self.start_date:
            self.start_date = self.end_date - timedelta(days=7)
        return self


def __compute_raster_response(
    result: RemoteSensingResult, body: DatafusionWorkUnit, request: Request
) -> GeoTiffResponse:
    file_uuid = uuid.uuid4()
    file_path = Path(f'/tmp/{file_uuid}.tiff')

    def unlink():
        file_path.unlink()

    with rio.open(
        file_path,
        mode='w+',
        driver='GTiff',
        height=result.height,
        width=result.width,
        count=1,
        dtype=str(result.index_data.dtype),
        crs=CRS.from_string('EPSG:4326'),
        nodata=None,
    ) as dst:
        dst.write(result.index_data[:, :, 0], 1)

    log.info(f'Finished for {body}')

    return GeoTiffResponse(
        file_path,
        media_type='image/geotiff',
        filename=f'{file_uuid}.tiff',
        background=BackgroundTask(unlink),
    )


# def aggregate_raster_response(polygon: gpd.GeoDataFrame, raster: GeoTiffResponse) -> JSONResponse:
def aggregate_raster_response(raster_name: str, df_vector: gpd.GeoDataFrame):
    with rio.open(raster_name, crs='EPSG:4326') as src:
        raster_rescaled = src.read(1)
        raster_rescaled[raster_rescaled < 0] = 0

        ndvi_stats_per_poly = zonal_stats(df_vector, raster_rescaled, affine=src.transform, stats='mean min max')
        df_vector['index_mean'] = [x['mean'] for x in ndvi_stats_per_poly]
        df_vector['index_min'] = [x['min'] for x in ndvi_stats_per_poly]
        df_vector['index_max'] = [x['max'] for x in ndvi_stats_per_poly]

    return df_vector.to_json()

import logging
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Tuple, Optional, List

import geojson_pydantic
import numpy as np
import rasterio
from pydantic import confloat, Field, BaseModel, model_validator
from rasterio.crs import CRS
from rasterstats import zonal_stats
from starlette.background import BackgroundTask
from starlette.responses import FileResponse

from naturalness.imagery_store_operator import Index

log = logging.getLogger(__name__)

NO_DATA_VALUES = {Index.NDVI: -999, Index.WATER: 0}


class GeoTiffResponse(FileResponse):
    media_type = 'image/geotiff'


@dataclass
class RemoteSensingResult:
    index_data: np.ndarray
    height: int
    width: int
    area_coords: Tuple[float, float, float, float]


class NaturalnessWorkUnit(BaseModel):
    """Area of interest for naturalness index"""

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
        'If not set it will be automatically set to one year before `end_date`',
        examples=['2023-05-01'],
        default=None,
    )
    end_date: date = Field(
        title='End Date',
        description="Upper bound (inclusive) of remote sensing imagery acquisition date (UTC). Defaults to today's date",
        examples=['2024-05-01'],
        default=datetime.now().date(),
    )

    @model_validator(mode='after')
    def minus_year(self) -> 'NaturalnessWorkUnit':
        if not self.start_date:
            self.start_date = self.end_date - timedelta(days=365)
        return self


def __compute_raster_response(
    raster_result: RemoteSensingResult,
    body: NaturalnessWorkUnit,
    index: Index,
) -> GeoTiffResponse:
    file_uuid = uuid.uuid4()
    file_path = Path(f'/tmp/{file_uuid}.tiff')

    def unlink():
        file_path.unlink()

    with rasterio.open(
        file_path,
        mode='w+',
        driver='GTiff',
        height=raster_result.height,
        width=raster_result.width,
        count=1,
        dtype=str(raster_result.index_data.dtype),
        crs=CRS.from_string('EPSG:4326'),
        nodata=NO_DATA_VALUES[index],
        transform=rasterio.transform.from_bounds(
            *raster_result.area_coords, width=raster_result.width, height=raster_result.height
        ),
    ) as dst:
        dst.write(raster_result.index_data, 1)

    log.info(f'Finished for {body}')

    return GeoTiffResponse(
        path=file_path,
        media_type='image/geotiff',
        filename=f'{file_uuid}.tiff',
        background=BackgroundTask(unlink),
    )


def __compute_vector_response(
    stats: List[str], vectors: geojson_pydantic.FeatureCollection, index: Index, raster_result: RemoteSensingResult
) -> geojson_pydantic.FeatureCollection:
    vector_result = aggregate_raster_response(
        stats=stats,
        geometries=vectors,
        index=index,
        raster_data=raster_result.index_data,
        affine=rasterio.transform.from_bounds(
            *raster_result.area_coords, width=raster_result.width, height=raster_result.height
        ),
    )

    return vector_result


def aggregate_raster_response(
    stats: List[str],
    geometries: geojson_pydantic.FeatureCollection,
    index: Index,
    raster_data: np.ndarray,
    affine: rasterio.Affine,
) -> geojson_pydantic.FeatureCollection:
    geojson = zonal_stats(
        vectors=geometries,
        raster=raster_data,
        stats=stats,
        affine=affine,
        geojson_out=True,
        nodata=NO_DATA_VALUES[index],
    )

    return geojson_pydantic.FeatureCollection(type='FeatureCollection', features=geojson)

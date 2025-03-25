import logging
import uuid
from datetime import date, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Tuple, Optional, List

import geojson_pydantic
import rasterio
import shapely
from pydantic import confloat, Field, BaseModel, model_validator
from rasterio.crs import CRS
from rasterstats import utils
from rasterstats import zonal_stats
from shapely.geometry import shape
from starlette.background import BackgroundTask
from starlette.responses import FileResponse

from naturalness.imagery_store_operator import Index, RemoteSensingResult

log = logging.getLogger(__name__)

NO_DATA_VALUES = {
    Index.NDVI: -999,
    Index.WATER: 255,
    Index.NATURALNESS: -999,
}

Aggregation = StrEnum('Aggregation', utils.VALID_STATS)


class GeoTiffResponse(FileResponse):
    media_type = 'image/geotiff'


class TimeRange(BaseModel):
    start_date: Optional[date] = Field(
        title='Start Date',
        description='Lower bound (inclusive) of remote sensing imagery acquisition date (UTC). '
        'If not set it will be automatically set to one year before `end_date`',
        examples=['2024-01-01'],
        default=None,
    )
    end_date: date = Field(
        title='End Date',
        description='Upper bound (inclusive) of remote sensing imagery acquisition date (UTC). '
        'Defaults to the 31st December of last year.',
        examples=['2024-12-31'],
        default=date(date.today().year - 1, 12, 31),
    )

    @model_validator(mode='after')
    def check_order(self) -> 'TimeRange':
        if self.start_date is not None:
            assert self.start_date < self.end_date, 'Start date must be before end date'
        return self

    @model_validator(mode='after')
    def minus_year(self) -> 'TimeRange':
        if not self.start_date:
            self.start_date = self.end_date - timedelta(days=365)
        return self


class NaturalnessWorkUnit(BaseModel):
    """Area of interest for naturalness index"""

    time_range: TimeRange = Field(
        title='Time Range',
        description='The time range of satellite observations to base the index on.',
        examples=[TimeRange()],
    )
    bbox: Tuple[
        confloat(ge=-180, le=180), confloat(ge=-90, le=90), confloat(ge=-180, le=180), confloat(ge=-90, le=90)
    ] = Field(
        title='Area Coordinates',
        description='Bounding box coordinates in WGS 84 (west, south, east, north)',
        examples=[[8.65, 49.38, 8.75, 49.41]],
    )


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
            *raster_result.bbox, width=raster_result.width, height=raster_result.height
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
    stats: List[Aggregation],
    vectors: geojson_pydantic.FeatureCollection,
    index: Index,
    raster_result: RemoteSensingResult,
) -> geojson_pydantic.FeatureCollection:
    geojson = zonal_stats(
        vectors=vectors,
        raster=raster_result.index_data,
        stats=stats,
        affine=rasterio.transform.from_bounds(
            *raster_result.bbox, width=raster_result.width, height=raster_result.height
        ),
        geojson_out=True,
        nodata=NO_DATA_VALUES[index],
    )

    return geojson_pydantic.FeatureCollection(type='FeatureCollection', features=geojson)


def get_bbox(features: geojson_pydantic.FeatureCollection) -> Tuple[float, float, float, float]:
    geoms = []
    for feature in features:
        geoms.append(shape(feature.geometry))
    return shapely.GeometryCollection(geoms).bounds

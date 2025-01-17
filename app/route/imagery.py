import datetime
import logging.config
from typing import Tuple, List

import geojson_pydantic
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from rasterstats import utils
from starlette.requests import Request

from app.route.common import (
    GeoTiffResponse,
    NaturalnessWorkUnit,
    __compute_raster_response,
    __compute_vector_response,
    RemoteSensingResult,
)
from naturalness.imagery_store_operator import ImageryStore, Index

log = logging.getLogger(__name__)

router = APIRouter(prefix='', tags=['index'])


@router.post(
    '/{index}/raster',
    description='Query index and return it as raster (GeoTIFF)',
    response_class=GeoTiffResponse,
)
async def index_compute_raster(index: Index, body: NaturalnessWorkUnit, request: Request) -> GeoTiffResponse:
    log.info(f'Creating index for {body}')

    raster_result = __provide_raster(
        index=index,
        bbox=body.area_coords,
        start_date=body.start_date,
        end_date=body.end_date,
        imagery_store=request.app.state.imagery_store,
    )
    return __compute_raster_response(raster_result=raster_result, body=body)


@router.post(
    '/{index}/vector',
    description='Query index and return it as vector (GeoJSON)',
    response_class=JSONResponse,
)
async def index_compute_vector(
    index: Index, aggregation_stats: List[str], body: NaturalnessWorkUnit, request: Request
) -> geojson_pydantic.Feature:
    log.info(f'Creating index for {body}')

    invalid_stats = set(aggregation_stats).difference(utils.VALID_STATS)
    if invalid_stats:
        raise HTTPException(
            status_code=422,
            detail=f'Summary statistic {invalid_stats} not supported.',
        )

    raster_result = __provide_raster(
        index=index,
        bbox=body.area_coords,
        start_date=body.start_date,
        end_date=body.end_date,
        imagery_store=request.app.state.imagery_store,
    )
    return __compute_vector_response(raster_result=raster_result, stats=aggregation_stats, body=body)


def __provide_raster(
    index: Index,
    bbox: Tuple[float, float, float, float],
    start_date: datetime.date,
    end_date: datetime.date,
    imagery_store: ImageryStore,
) -> RemoteSensingResult:
    index_data, (h, w) = imagery_store.imagery(
        index=index, area_coords=bbox, start_date=start_date.isoformat(), end_date=end_date.isoformat()
    )
    log.info('Query index as raster values completed')

    return RemoteSensingResult(index_data, h, w, bbox)

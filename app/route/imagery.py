import datetime
import logging.config
from typing import Tuple, List

import geojson_pydantic
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from starlette.requests import Request

from app.route.common import (
    GeoTiffResponse,
    NaturalnessWorkUnit,
    __compute_raster_response,
    __compute_vector_response,
    RemoteSensingResult,
    Aggregation,
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
    return __compute_raster_response(raster_result=raster_result, body=body, index=index)


@router.post(
    '/{index}/vector',
    description='Query index and return it as vector (GeoJSON)',
    response_class=JSONResponse,
)
async def index_compute_vector(
    index: Index,
    aggregation_stats: List[Aggregation],
    vectors: geojson_pydantic.FeatureCollection,
    body: NaturalnessWorkUnit,
    request: Request,
) -> geojson_pydantic.FeatureCollection:
    log.info(f'Creating index for {body}')

    raster_result = __provide_raster(
        index=index,
        bbox=body.area_coords,
        start_date=body.start_date,
        end_date=body.end_date,
        imagery_store=request.app.state.imagery_store,
    )

    vector_response = __compute_vector_response(
        stats=aggregation_stats,
        vectors=vectors,
        index=index,
        raster_result=raster_result,
    )
    log.info(f'Finished for {body}')

    return vector_response


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

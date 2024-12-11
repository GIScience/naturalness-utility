import datetime
import logging.config
from typing import Tuple

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from omegaconf import OmegaConf
from starlette.requests import Request

from app.route.common import (
    GeoTiffResponse,
    DatafusionWorkUnit,
    __compute_raster_response,
    __compute_vector_response,
    RemoteSensingResult,
)
from datafusion.imagery_store_operator import ImageryStore

log = logging.getLogger(__name__)

cfg = OmegaConf.load('settings.yaml')
index_name = list(cfg.index_name)[0]

router = APIRouter(prefix=f'/{index_name}', tags=['index'])


@router.post(
    '/raster',
    description='Query index and return it as raster (GeoTIFF)',
    response_class=GeoTiffResponse,
)
async def index_compute_raster(body: DatafusionWorkUnit, request: Request):
    log.info(f'Creating index for {body}')

    raster_result = __provide_raster(
        bbox=body.area_coords,
        imagery_store=request.app.state.imagery_store,
        start_date=body.start_date,
        end_date=body.end_date,
    )
    return __compute_raster_response(raster_result=raster_result, body=body)


@router.post(
    '/vector',
    description='Query index and return it as vector (GeoJSON)',
    response_class=JSONResponse,
)
async def index_compute_vector(body: DatafusionWorkUnit, request: Request):
    log.info(f'Creating index for {body}')

    raster_result = __provide_raster(
        bbox=body.area_coords,
        imagery_store=request.app.state.imagery_store,
        start_date=body.start_date,
        end_date=body.end_date,
    )
    return __compute_vector_response(raster_result, body, request)


def __provide_raster(
    bbox: Tuple[float, float, float, float],
    imagery_store: ImageryStore,
    start_date: datetime.date,
    end_date: datetime.date,
) -> RemoteSensingResult:
    index_data, (h, w) = imagery_store.imagery(
        area_coords=bbox, start_date=start_date.isoformat(), end_date=end_date.isoformat()
    )
    log.info('Query index as raster values completed')

    return RemoteSensingResult(index_data, h, w, bbox)

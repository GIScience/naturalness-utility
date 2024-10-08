import logging.config
from fastapi.responses import JSONResponse
from omegaconf import OmegaConf
from sentinelhub import BBox, CRS as SCRS, to_utm_bbox
from fastapi import APIRouter, HTTPException
from starlette.requests import Request

from app.route.common import (
    GeoTiffResponse,
    DatafusionWorkUnit,
    RemoteSensingResult,
    __compute_raster_response,
    __compute_vector_response,
)


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
    try:
        raster_result = __provide_raster(body, request)
        return __compute_raster_response(raster_result, body, request)[0]
    except AssertionError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.post(
    '/vector',
    description='Query index and return it as vector (GeoJSON)',
    response_class=JSONResponse,
)
async def index_compute_vector(body: DatafusionWorkUnit, request: Request):
    log.info(f'Creating index for {body}')

    try:
        raster_result = __provide_raster(body, request)
        return __compute_vector_response(raster_result, body, request)[0]

    except AssertionError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


def __provide_raster(body: DatafusionWorkUnit, request: Request) -> RemoteSensingResult:
    bbox = to_utm_bbox(BBox(bbox=body.area_coords, crs=SCRS.WGS84))
    imagery_store = request.app.state.imagery_store

    index_data, (h, w) = imagery_store.imagery(
        area_coords=bbox,
        start_date=body.start_date.isoformat(),
        end_date=body.end_date.isoformat(),
        save_data=body.save_data,
    )
    log.info('Query index as raster values completed')

    return RemoteSensingResult(index_data, h, w, bbox)

import logging.config
from omegaconf import OmegaConf
from sentinelhub import BBox, CRS as SCRS, to_utm_bbox
from fastapi import APIRouter, HTTPException
from starlette.requests import Request

from app.route.common import DatafusionWorkUnit, RemoteSensingResult, __compute_raster_response


log = logging.getLogger(__name__)

cfg = OmegaConf.load('settings.yaml')
router = APIRouter(prefix='/raster', tags=[cfg.index_name])


@router.post(
    '/',
    description='Query index and return it as raster (GeoTIFF)',
)
async def index_compute(body: DatafusionWorkUnit, request: Request):
    log.info(f'Creating index for {body}')
    try:
        result = __provide(body, request)
        return __compute_raster_response(result, body, request)
    except AssertionError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


def __provide(body: DatafusionWorkUnit, request: Request) -> RemoteSensingResult:
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

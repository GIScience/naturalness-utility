import logging.config
from typing import Annotated, List

import geojson_pydantic
from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from pydantic import conint
from sentinelhub import CRS, BBox, bbox_to_dimensions
from starlette.requests import Request

from app.route.common import (
    Aggregation,
    GeoTiffResponse,
    NaturalnessWorkUnit,
    PuEstimationResponse,
    TimeRange,
    __compute_raster_response,
    __compute_vector_response,
    get_bbox,
)
from naturalness.imagery_store_operator import Index

log = logging.getLogger(__name__)

router = APIRouter(prefix='', tags=['index'])


@router.post(
    '/{index}/raster',
    summary='Index values as raster',
    description='Retrieve the requested index and return its raw data as raster (GeoTIFF)',
    response_class=GeoTiffResponse,
)
async def index_compute_raster(index: Index, body: NaturalnessWorkUnit, request: Request) -> GeoTiffResponse:
    log.info(f'Creating index for {body}')

    raster_result = request.app.state.imagery_store.imagery(
        index=index,
        bbox=body.bbox,
        start_date=body.time_range.start_date.isoformat(),
        end_date=body.time_range.end_date.isoformat(),
        resolution=body.resolution,
    )
    return __compute_raster_response(raster_result=raster_result, body=body, index=index)


@router.post(
    '/{index}/vector',
    summary='Aggregate index values to user-defined regions',
    description='Retrieve the requested index and compute a summary of the values within the given vector geometry (GeoJSON)',
    response_class=JSONResponse,
)
async def index_compute_vector(
    index: Index,
    aggregation_stats: Annotated[List[Aggregation], Body(examples=[[Aggregation.median]])],
    vectors: Annotated[
        geojson_pydantic.FeatureCollection,
        Body(
            examples=[
                {
                    'type': 'FeatureCollection',
                    'features': [
                        {
                            'type': 'Feature',
                            'properties': {},
                            'geometry': {
                                'coordinates': [
                                    [[8.70, 49.41], [8.70, 49.42], [8.71, 49.42], [8.71, 49.41], [8.70, 49.41]]
                                ],
                                'type': 'Polygon',
                            },
                        }
                    ],
                }
            ]
        ),
    ],
    time_range: TimeRange,
    request: Request,
    resolution: Annotated[conint(ge=10), Body()] = 90,
) -> geojson_pydantic.FeatureCollection:
    log.info(f'Creating index for {time_range}')

    raster_result = request.app.state.imagery_store.imagery(
        index=index,
        bbox=get_bbox(features=vectors),
        start_date=time_range.start_date.isoformat(),
        end_date=time_range.end_date.isoformat(),
        resolution=resolution,
    )

    vector_response = __compute_vector_response(
        stats=aggregation_stats,
        vectors=vectors,
        index=index,
        raster_result=raster_result,
    )
    log.info(f'Finished for {time_range}')

    return vector_response


@router.post(
    '/{index}/raster/estimate_pus',
    summary='Estimate processing units required.',
    description='Use the provided work unit to estimate how many processing units will be consumed in the request.',
)
async def index_estimate_raster_pus(index: Index, body: NaturalnessWorkUnit, request: Request) -> PuEstimationResponse:
    bbox_obj = BBox(bbox=body.bbox, crs=CRS.WGS84)
    bbox_width, bbox_height = bbox_to_dimensions(bbox_obj, resolution=body.resolution)
    sh_request = request.app.state.imagery_store.construct_sentinel_request(
        index=index,
        start_date=body.time_range.start_date,
        end_date=body.time_range.end_date,
        bbox=bbox_obj,
        bbox_shape=(bbox_width, bbox_height),
    )
    estimated_pus = request.app.state.imagery_store.estimate_pus(index=index, request=sh_request)
    return PuEstimationResponse(
        estimated_pus=estimated_pus.estimated, pu_quota_per_minute=request.app.state.imagery_store.pu_quota_per_minute
    )

import logging.config
from typing import List, Annotated

import geojson_pydantic
from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from starlette.requests import Request

from app.route.common import (
    GeoTiffResponse,
    NaturalnessWorkUnit,
    __compute_raster_response,
    __compute_vector_response,
    TimeRange,
    get_bbox,
    Aggregation,
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
                                    [[8.66, 49.42], [8.66, 49.41], [8.67, 49.41], [8.67, 49.42], [8.66, 49.42]]
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
) -> geojson_pydantic.FeatureCollection:
    log.info(f'Creating index for {time_range}')

    raster_result = request.app.state.imagery_store.imagery(
        index=index,
        bbox=get_bbox(features=vectors),
        start_date=time_range.start_date.isoformat(),
        end_date=time_range.end_date.isoformat(),
    )

    vector_response = __compute_vector_response(
        stats=aggregation_stats,
        vectors=vectors,
        index=index,
        raster_result=raster_result,
    )
    log.info(f'Finished for {time_range}')

    return vector_response

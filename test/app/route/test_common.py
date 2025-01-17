from datetime import date

import geojson_pydantic
import numpy as np
import rasterio

from app.route.common import RemoteSensingResult, aggregate_raster_response, NaturalnessWorkUnit


def test_naturalness_work_unit():
    area_coords = (8.65, 49.38, 8.75, 49.41)
    start_date = date(2020, 1, 1)
    end_date = date(2020, 2, 1)
    wu = NaturalnessWorkUnit(
        area_coords=area_coords,
        start_date=start_date,
        end_date=end_date,
    )

    assert wu.area_coords == area_coords
    assert wu.start_date == start_date
    assert wu.end_date == end_date


def test_naturalness_work_unit_infer_date_start():
    area_coords = (8.65, 49.38, 8.75, 49.41)

    end_date = date(2020, 1, 8)
    wu = NaturalnessWorkUnit(
        area_coords=area_coords,
        end_date=end_date,
    )

    assert wu.start_date == date(2020, 1, 1)


def test_aggregate_raster_response():
    area_coords = (8.65, 49.38, 8.75, 49.41)
    xmin, ymin, xmax, ymax = area_coords
    test_aoi = geojson_pydantic.Polygon(
        type='Polygon', coordinates=[[[xmin, ymin], [xmax, ymin], [xmax, ymax], [xmin, ymax], [xmin, ymin]]]
    )

    test_raster_result = RemoteSensingResult(
        index_data=np.round(np.random.rand(331, 727), decimals=4),
        height=331,
        width=727,
        area_coords=area_coords,
    )

    geom = aggregate_raster_response(
        geometry=test_aoi,
        raster_data=test_raster_result.index_data,
        stats={'max'},
        affine=rasterio.transform.from_bounds(
            *test_raster_result.area_coords, width=test_raster_result.width, height=test_raster_result.height
        ),
    )

    assert geom.properties['max'] == test_raster_result.index_data.max()

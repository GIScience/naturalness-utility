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
    area_coords = (0.0, 0.0, 2.0, 2.0)
    test_geometries = [
        geojson_pydantic.Polygon(
            type='Polygon', coordinates=[[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]]
        ),
        geojson_pydantic.Polygon(
            type='Polygon', coordinates=[[[0.0, 0.0], [2.0, 0.0], [2.0, 2.0], [0.0, 2.0], [0.0, 0.0]]]
        ),
    ]
    data = np.ones(shape=(20, 20))
    data[10:, :10] = 0.5

    test_raster_result = RemoteSensingResult(
        index_data=data,
        height=data.shape[0],
        width=data.shape[1],
        area_coords=area_coords,
    )

    geom = aggregate_raster_response(
        stats={'max'},
        geometries=test_geometries,
        raster_data=test_raster_result.index_data,
        affine=rasterio.transform.from_bounds(
            *test_raster_result.area_coords, width=test_raster_result.width, height=test_raster_result.height
        ),
    )

    assert isinstance(geom, geojson_pydantic.FeatureCollection)
    for g_in, g_out in zip(test_geometries, geom):
        assert g_in == g_out.geometry

    assert geom[0].properties['max'] == 0.5
    assert geom[1].properties['max'] == 1.0

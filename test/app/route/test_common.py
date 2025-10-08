from datetime import date

import geojson_pydantic
import numpy as np
import pytest
from pydantic import ValidationError

from app.route.common import Aggregation, NaturalnessWorkUnit, TimeRange, __compute_vector_response, get_bbox
from naturalness.imagery_store_operator import Index, ProcessingUnitStats, RemoteSensingResult


def test_time_range_infer_date_start():
    end_date = date(2020, 1, 8)

    time_range = TimeRange(end_date=end_date)

    assert time_range.start_date == date(2019, 1, 8)


def test_time_range_correct_order():
    with pytest.raises(ValidationError, match=r'.*Start date must be before end date.*'):
        TimeRange(start_date=date(2020, 1, 8), end_date=date(2019, 1, 8))


def test_work_unit():
    bbox = (8.65, 49.38, 8.75, 49.41)
    start_date = date(2020, 1, 1)
    end_date = date(2020, 2, 1)
    wu = NaturalnessWorkUnit(time_range=TimeRange(start_date=start_date, end_date=end_date), bbox=bbox)

    assert wu.bbox == bbox
    assert wu.time_range.start_date == start_date
    assert wu.time_range.end_date == end_date


def test_compute_vector_response():
    bbox = (0.0, 0.0, 2.0, 2.0)
    test_geometries = geojson_pydantic.FeatureCollection.model_validate(
        {
            'type': 'FeatureCollection',
            'features': [
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Polygon',
                        'coordinates': [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]],
                    },
                    'properties': {},
                },
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Polygon',
                        'coordinates': [[[0.0, 0.0], [2.0, 0.0], [2.0, 2.0], [0.0, 2.0], [0.0, 0.0]]],
                    },
                    'properties': {},
                },
            ],
        }
    )
    data = np.ones(shape=(20, 20))
    data[10:, :10] = 0.5

    test_raster_result = RemoteSensingResult(
        index_data=data,
        height=data.shape[0],
        width=data.shape[1],
        bbox=bbox,
        pus=ProcessingUnitStats(estimated=12, consumed=12),
    )

    geom = __compute_vector_response(
        stats=[Aggregation.max],
        vectors=test_geometries,
        index=Index.NDVI,
        raster_result=test_raster_result,
    )

    assert isinstance(geom, geojson_pydantic.FeatureCollection)
    for g_in, g_out in zip(test_geometries.iter(), geom.iter()):
        assert g_in.geometry == g_out.geometry

    assert geom.features[1].properties['max'] == 1.0
    assert geom.features[0].properties['max'] == 0.5


def test_compute_vector_response_polygon_smaller_than_raster_cell():
    bbox = (0.0, 0.0, 2.0, 2.0)
    test_geometries = geojson_pydantic.FeatureCollection.model_validate(
        {
            'type': 'FeatureCollection',
            'features': [
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Polygon',
                        'coordinates': [[[0.0, 0.0], [0.1, 0.0], [0.1, 0.1], [0.0, 0.1], [0.0, 0.0]]],
                    },
                    'properties': {},
                },
            ],
        }
    )
    data = np.ones(shape=(2, 2))

    test_raster_result = RemoteSensingResult(
        index_data=data,
        height=data.shape[0],
        width=data.shape[1],
        bbox=bbox,
        pus=ProcessingUnitStats(estimated=12, consumed=12),
    )

    geom = __compute_vector_response(
        stats=[Aggregation.max],
        vectors=test_geometries,
        index=Index.NDVI,
        raster_result=test_raster_result,
    )

    assert geom.features[0].properties['max'] == 1.0


def test_get_bbox(default_feature_collection):
    computed_bbox = get_bbox(default_feature_collection)
    assert computed_bbox == (0.0, 0.0, 1.0, 1.0)

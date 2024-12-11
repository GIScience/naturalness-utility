import numpy as np
import json
import pandas as pd

from app.route.common import aggregate_raster_response


import pytest


TEST_raster_path = './test/test_data/test_raster.tiff'
TEST_vector_path = './test/test_data/test_vector.geojson'


@pytest.mark.parametrize(
    'TEST_raster_path, TEST_vector_path, expected_mean, expected_median, expected_min, expected_max',
    [
        (
            TEST_raster_path,
            TEST_vector_path,
            [0.8675, 0.6822, 0.8074],
            [0.8675, 0.8181, 0.8627],
            [0.8675, 0.2126, 0.1433],
            [0.8675, 0.9115, 0.9398],
        ),
    ],
)
def test_aggregate_raster_response(
    TEST_raster_path, TEST_vector_path, expected_mean, expected_median, expected_min, expected_max
):
    geom = aggregate_raster_response(TEST_raster_path, TEST_vector_path)
    df_geom = pd.json_normalize(json.loads(geom)['features'])
    df_geom = np.round(df_geom, 4)

    assert list(df_geom['properties.index_mean'].values) == expected_mean
    assert list(df_geom['properties.index_median'].values) == expected_median
    assert list(df_geom['properties.index_min'].values) == expected_min
    assert list(df_geom['properties.index_max'].values) == expected_max

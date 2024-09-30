import numpy as np
import json
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon

from app.route.common import aggregate_raster_response

import pytest


TEST_raster_path = './test/test_data/test_raster.tiff'

TEST_vector = gpd.GeoDataFrame(
    {
        'name': ['poly1', 'poly2'],
        'geometry': [
            Polygon(((7.384, 47.517), (7.385, 47.515), (7.380, 47.52), (7.385, 47.50))),
            Polygon(((7.38, 47.515), (7.385, 47.515), (7.385, 47.519), (7.385, 47.519))),
        ],
    },
    crs=None,
)


@pytest.mark.parametrize(
    'TEST_raster_path, TEST_vector, expected_mean, expected_min, expected_max',
    [
        (TEST_raster_path, TEST_vector, [0.807360, 0.723762], [0.143302, 0.143302], [0.939826, 0.927506]),
    ],
)
def test_aggregate_raster_response(TEST_raster_path, TEST_vector, expected_mean, expected_min, expected_max):
    geom = aggregate_raster_response(TEST_raster_path, TEST_vector)
    df_geom = pd.json_normalize(json.loads(geom)['features'])
    df_geom = np.round(df_geom, 6)

    assert list(df_geom['properties.index_mean'].values) == expected_mean
    assert list(df_geom['properties.index_min'].values) == expected_min
    assert list(df_geom['properties.index_max'].values) == expected_max

import numpy as np
import json
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon

from app.route.common import aggregate_raster_response

import pytest


TEST_raster_name = '/home/buch/Documents/HeiGIT/datafusion-utility/test/test_response.tiff'

TEST_vector = gpd.GeoDataFrame(
    {
        'name': ['poly1', 'poly2'],
        'geometry': [
            Polygon(((8.8, 49.40), (8.60, 49.415), (8.70, 49.40), (8.70, 49.40))),
            Polygon(((8.8, 49.38), (8.60, 49.36), (8.70, 49.39), (8.70, 49.36))),
        ],
    },
    crs='EPSG:4326',
)


## FIXME: replace with dummy raster whihc will be deleted after testing
@pytest.mark.parametrize(
    'TEST_raster_name, TEST_vector, expected_mean, expected_min, expected_max',
    [
        (TEST_raster_name, TEST_vector, [0.612142, 0.577751], [0.0, 0.0], [0.921961, 0.922032]),
    ],
)  # TODO add further test cases
def test_aggregate_raster_response(TEST_raster_name, TEST_vector, expected_mean, expected_min, expected_max):
    geom = aggregate_raster_response(TEST_raster_name, TEST_vector)
    df_geom = pd.json_normalize(json.loads(geom)['features'])
    df_geom = np.round(df_geom, 6)
    assert list(df_geom['properties.index_mean'].values) == expected_mean
    assert list(df_geom['properties.index_min'].values) == expected_min
    assert list(df_geom['properties.index_max'].values) == expected_max

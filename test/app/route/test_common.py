import numpy as np
import json
import pandas as pd

from app.route.common import aggregate_raster_response

# from unittest.mock import patch, MagicMock
# from app.route.common import __compute_vector_response, RemoteSensingResult, DatafusionWorkUnit
# from starlette.requests import Request
# from starlette.responses import JSONResponse

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

    # @pytest.fixture
    # def mock_raster_result():
    #     return RemoteSensingResult(
    #         index_data=np.random.rand(100, 100, 1),
    #         height=100,
    #         width=100,
    #         area_coords=(8.65, 49.38, 8.75, 49.41)
    #     )

    # @pytest.fixture
    # def mock_body():
    #     return DatafusionWorkUnit(
    #         area_coords=(8.65, 49.38, 8.75, 49.41),
    #         start_date=None,
    #         end_date=datetime.now().date(),
    #         save_data=True,
    #         vector_path='./test/test_data/test_vector.geojson'
    #     )

    # @pytest.fixture
    # def mock_request():
    #     return MagicMock(Request)

    # @patch('app.route.common.__compute_raster_response')
    # @patch('app.route.common.aggregate_raster_response')
    # def test_compute_vector_response(mock_aggregate_raster_response, mock_compute_raster_response, mock_raster_result, mock_body, mock_request):
    #     mock_compute_raster_response.return_value = (MagicMock(), '/tmp/mock_raster_path.tiff')  # TODO check
    #     mock_aggregate_raster_response.return_value = {
    #         "type": "FeatureCollection",
    #         "features": [
    #             {
    #                 "type": "Feature",
    #                 "properties": {
    #                     "index_mean": 0.8,
    #                     "index_min": 0.1,
    #                     "index_max": 0.9
    #                 },
    #                 "geometry": {
    #                     "type": "Polygon",
    #                     "coordinates": [[[8.65, 49.38], [8.75, 49.38], [8.75, 49.41], [8.65, 49.41], [8.65, 49.38]]]
    #                 }
    #             } ] }

    #     response, file_path = __compute_vector_response(mock_raster_result, mock_body, mock_request)

    #     assert isinstance(response, JSONResponse)
    #     assert response.status_code == 200

    #     response_data = json.loads(response.body)
    #     assert "features" in response_data
    #     assert len(response_data["features"]) > 0
    #     assert "index_mean" in response_data["features"][0]["properties"]
    #     assert "index_min" in response_data["features"][0]["properties"]
    #     assert "index_max" in response_data["features"][0]["properties"]

    #     assert file_path.exists()

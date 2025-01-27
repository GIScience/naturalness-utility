from datetime import datetime, timedelta

import numpy as np
import pytest
from rasterio import MemoryFile

from app.route.common import RemoteSensingResult, Aggregation
from app.route.imagery import __provide_raster
from naturalness.imagery_store_operator import Index
from test.conftest import TestImageryStore


def test_provide_raster():
    expected_result = RemoteSensingResult(
        index_data=np.array(True), height=2, width=3, area_coords=(0.0, 0.0, 1.0, 1.0)
    )

    bbox = (0.0, 0.0, 1.0, 1.0)
    imagery_store = TestImageryStore()
    computed_remote_sensing_result = __provide_raster(
        index=Index.NDVI,
        bbox=bbox,
        imagery_store=imagery_store,
        start_date=datetime.now() - timedelta(days=7),
        end_date=datetime.now(),
    )

    assert computed_remote_sensing_result.index_data.shape == (expected_result.height, expected_result.width)


@pytest.mark.parametrize('index', Index)
def test_index_raster(mocked_client, index):
    request_body = {
        'area_coords': [0.0, 0.0, 1.0, 1.0],
        'end_date': '2023-06-01',
    }

    response = mocked_client.post(f'/{index}/raster', json=request_body)

    assert response.status_code == 200
    assert response.headers['content-type'] == 'image/geotiff'

    with MemoryFile(response.content) as memfile:
        with memfile.open() as dataset:
            response_data = dataset.read(masked=True)

            response_mask = response_data.mask
            response_values = np.ma.getdata(response_data)

    match index:
        case Index.NDVI:
            expected_result = np.array([[[0.0, 0.5, 1.0], [-999.0, 1.0, 1.0]]])
            expected_mask = np.array([[[False, False, False], [True, False, False]]])

            np.testing.assert_array_equal(response_values, expected_result)
            np.testing.assert_array_equal(response_mask, expected_mask)
        case Index.WATER:
            expected_result = np.array([[[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]]])
            expected_mask = np.array([[[True, True, True], [False, False, False]]])

            np.testing.assert_array_equal(response_values, expected_result)
            np.testing.assert_array_equal(response_mask, expected_mask)
        case _:
            assert False, f'Test from {index} not implemented'


@pytest.mark.parametrize('index', Index)
def test_index_vector(mocked_client, index, default_vector_request):
    response = mocked_client.post(f'/{index}/vector', json=default_vector_request)

    assert response.status_code == 200
    assert response.headers['content-type'] == 'application/json'

    response_feature = response.json()['features'][0]

    assert response_feature['geometry'] == default_vector_request['vectors']['features'][0]['geometry']

    match index:
        case Index.NDVI:
            np.testing.assert_almost_equal(response_feature['properties']['max'], 1.0)
        case Index.WATER:
            np.testing.assert_almost_equal(response_feature['properties']['max'], 1.0)
        case _:
            assert False, f'Test from {index} not implemented'


@pytest.mark.parametrize('index', Index)
def test_index_vector_multi_agg(mocked_client, index, default_vector_request):
    default_vector_request.update({'aggregation_stats': [Aggregation.max, Aggregation.min]})

    response = mocked_client.post(f'/{index}/vector', json=default_vector_request)

    assert response.status_code == 200
    assert response.headers['content-type'] == 'application/json'

    response_feature = response.json()['features'][0]

    assert response_feature['geometry'] == {
        'type': 'Polygon',
        'coordinates': [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]],
    }

    match index:
        case Index.NDVI:
            np.testing.assert_almost_equal(response_feature['properties']['max'], 1.0)
            np.testing.assert_almost_equal(response_feature['properties']['min'], 0.0)
        case Index.WATER:
            np.testing.assert_almost_equal(response_feature['properties']['max'], 1.0)
            np.testing.assert_almost_equal(response_feature['properties']['min'], 1.0)
        case _:
            assert False, f'Test from {index} not implemented'


@pytest.mark.parametrize('index', Index)
def test_index_vector_raise_exception_invalid_summary(mocked_client, index, default_vector_request):
    default_vector_request.update({'aggregation_stats': [Aggregation.max, 'foo']})

    response = mocked_client.post(f'/{index}/vector', json=default_vector_request)
    assert response.status_code == 422

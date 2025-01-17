from datetime import datetime, timedelta

import numpy as np
import pytest
from rasterio import MemoryFile

from app.route.common import RemoteSensingResult
from app.route.imagery import __provide_raster
from test.conftest import TestImageryStore
from naturalness.imagery_store_operator import Index


def test_provide_raster():
    expected_result = RemoteSensingResult(
        index_data=np.array(True), height=93, width=100, area_coords=(0.0, 0.0, 1.0, 1.0)
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
        'area_coords': [
            7.3828125,
            47.5172006978394,
            7.395859375,
            47.52578359086485,
        ],
        'end_date': '2023-06-01',
    }

    response = mocked_client.post(f'/{index}/raster', json=request_body)

    assert response.status_code == 200
    assert response.headers['content-type'] == 'image/geotiff'

    with MemoryFile(response.content) as memfile:
        with memfile.open() as dataset:
            response_data = dataset.read()

    assert response_data.shape == (1, 93, 100)
    assert response_data.sum() > 0


@pytest.mark.parametrize('index', Index)
def test_index_vector(mocked_client, index):
    request_body = {
        'body': {
            'area_coords': [
                0,
                0,
                1,
                1,
            ],
            'end_date': '2023-06-01',
        },
        'aggregation_stats': ['max'],
    }

    response = mocked_client.post(f'/{index}/vector', json=request_body)

    assert response.status_code == 200
    assert response.headers['content-type'] == 'application/json'

    response_data = response.json()

    assert 0.0 <= response_data['properties']['max'] <= 1.0
    assert response_data['geometry'] == {
        'type': 'Polygon',
        'coordinates': [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]],
    }


@pytest.mark.parametrize('index', Index)
def test_index_vector_multi_agg(mocked_client, index):
    request_body = {
        'body': {
            'area_coords': [
                0,
                0,
                1,
                1,
            ],
            'end_date': '2023-06-01',
        },
        'aggregation_stats': ['max', 'min'],
    }

    response = mocked_client.post(f'/{index}/vector', json=request_body)

    assert response.status_code == 200
    assert response.headers['content-type'] == 'application/json'

    response_data = response.json()

    assert 0.0 <= response_data['properties']['max'] <= 1.0
    assert 0.0 <= response_data['properties']['min'] <= 1.0
    assert response_data['geometry'] == {
        'type': 'Polygon',
        'coordinates': [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]],
    }


@pytest.mark.parametrize('index', Index)
def test_index_vector_raise_exception_invalid_summary(mocked_client, index):
    request_body = {
        'body': {
            'area_coords': [
                0,
                0,
                1,
                1,
            ],
            'end_date': '2023-06-01',
        },
        'aggregation_stats': ['min', 'foo'],
    }

    response = mocked_client.post(f'/{index}/vector', json=request_body)
    assert response.status_code == 422
    assert response.text == '{"detail":"Summary statistic {\'foo\'} not supported."}'

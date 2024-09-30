import io
from datetime import datetime, timedelta
from typing import Dict, Tuple

import numpy as np
from omegaconf import OmegaConf
from tifffile import imread
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.api import app
from app.route import imagery
from datafusion.imagery_store_operator import ImageryStore


import pytest
from unittest.mock import Mock

TODAY = datetime.now().date().isoformat()
WEEK_BEFORE = (datetime.now() - timedelta(days=7)).date().isoformat()

cfg = OmegaConf.load('settings.yaml')
INDEX_NAME = list(cfg.index_name)[0]


TEST_JSON_start_end = {
    'area_coords': [
        7.3828125,
        47.5172006978394,
        7.395859375,
        47.52578359086485,
    ],
    'start_date': '2023-05-01',
    'end_date': '2023-06-01',
}

TEST_JSON_no_time = {
    'area_coords': [
        7.3828125,
        47.5172006978394,
        7.395859375,
        47.52578359086485,
    ],
    'save_data': False,
}


class TestImageryStore(ImageryStore):
    def __init__(self):
        self.last_start_date = None
        self.last_end_date = None
        self.save_data = None

    def imagery(
        self,
        area_coords: Tuple,
        start_date: str,
        end_date: str,
        resolution: int = 10,
        save_data: bool = False,
    ) -> tuple[Dict[str, np.ndarray], tuple[int, int]]:
        self.last_start_date = start_date
        self.last_end_date = end_date
        self.save_data = save_data

        return np.random.uniform(0.0, 1.0, (93, 100, 1)).astype(np.float32), (93, 100)


@pytest.fixture
def mocked_client():
    client = TestClient(app)
    app.state.imagery_store = TestImageryStore()

    yield client


@pytest.fixture
def mocked_imagery_store():
    app = FastAPI()
    app.include_router(imagery.router)
    app.state.imagery_store = Mock()

    yield TestClient(app), app.state.imagery_store


def test_health(mocked_client):
    response = mocked_client.get('/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}


@pytest.mark.parametrize(
    'request_body, expected_start_date, expected_end_date, expected_saving',
    [
        (TEST_JSON_start_end, '2023-05-01', '2023-06-01', True),
        (TEST_JSON_no_time, WEEK_BEFORE, TODAY, False),
    ],
)
def test_index_raster(mocked_client, request_body, expected_start_date, expected_end_date, expected_saving):
    mocked_client.app.state.imagery_store = TestImageryStore()

    response = mocked_client.post(f'/{INDEX_NAME}/raster', json=request_body)
    response_data = imread(io.BytesIO(response.content))

    assert response.status_code == 200
    assert response.headers['content-type'] == 'image/geotiff'
    assert mocked_client.app.state.imagery_store.last_start_date == expected_start_date
    assert mocked_client.app.state.imagery_store.last_end_date == expected_end_date
    assert mocked_client.app.state.imagery_store.save_data == expected_saving

    assert response_data.shape == (93, 100)
    assert response_data.sum() > 0


@pytest.mark.parametrize(
    'request_body, expected_start_date, expected_end_date, expected_saving',
    [
        (TEST_JSON_start_end, '2023-05-01', '2023-06-01', True),
        (TEST_JSON_no_time, WEEK_BEFORE, TODAY, False),
    ],
)
def test_index_vector(mocked_client, request_body, expected_start_date, expected_end_date, expected_saving):
    mocked_client.app.state.imagery_store = TestImageryStore()

    response_vector = mocked_client.post(f'/{INDEX_NAME}/vector', json=request_body)

    assert response_vector.status_code == 200
    assert response_vector.headers['content-type'] == 'application/json'
    assert mocked_client.app.state.imagery_store.last_start_date == expected_start_date
    assert mocked_client.app.state.imagery_store.last_end_date == expected_end_date
    assert mocked_client.app.state.imagery_store.save_data == expected_saving


def test_errorneous_json(mocked_client):
    response = mocked_client.post(f'/{INDEX_NAME}/raster', json={})

    assert response.status_code == 422


def test_imagery_store_raises_assertion_error_should_fail(mocked_imagery_store):
    app, imagery_store = mocked_imagery_store

    imagery_store.imagery.side_effect = AssertionError('something went wrong')
    response = app.post(f'/{INDEX_NAME}/raster', json=TEST_JSON_start_end)

    assert response.status_code == 400
    assert response.json() == {'detail': 'something went wrong'}

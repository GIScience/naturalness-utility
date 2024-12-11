import io
import json
from datetime import datetime, timedelta
from typing import Tuple
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from omegaconf import OmegaConf
from tifffile import imread

from app.api import app
from app.route import imagery
from datafusion.imagery_store_operator import ImageryStore

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
    'vector_path': './test/test_data/test_vector.geojson',
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
        area_coords: Tuple[float, float, float, float],
        start_date: str,
        end_date: str,
        resolution: int = 10,
        save_data: bool = False,
    ) -> tuple[np.ndarray, tuple[int, int]]:
        self.last_start_date = start_date
        self.last_end_date = end_date
        self.save_data = save_data

        return np.random.uniform(0.0, 1.0, (93, 100)).astype(np.float32), (93, 100)


def test_test_imagery_store():
    bbox = (0.0, 0.0, 1.0, 1.0)
    imagery_store = TestImageryStore()
    computed_remote_sensing_result = imagery_store.imagery(
        area_coords=bbox,
        start_date=(datetime.now() - timedelta(days=7)).isoformat(),
        end_date=datetime.now().isoformat(),
    )
    assert computed_remote_sensing_result[0].max() >= 0
    assert computed_remote_sensing_result[0].min() <= 1


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
        (TEST_JSON_start_end, '2023-05-01', '2023-06-01', False),
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
        (TEST_JSON_start_end, '2023-05-01', '2023-06-01', False),
        (TEST_JSON_no_time, WEEK_BEFORE, TODAY, False),
    ],
)
def test_index_vector(mocked_client, request_body, expected_start_date, expected_end_date, expected_saving):
    mocked_client.app.state.imagery_store = TestImageryStore()

    response = mocked_client.post(f'/{INDEX_NAME}/vector', json=request_body)
    response_data = response.json()
    response_data = pd.json_normalize(json.loads(response_data)['features'])

    assert response.status_code == 200
    assert response.headers['content-type'] == 'application/json'
    assert mocked_client.app.state.imagery_store.last_start_date == expected_start_date
    assert mocked_client.app.state.imagery_store.last_end_date == expected_end_date
    assert mocked_client.app.state.imagery_store.save_data == expected_saving

    assert response_data['properties.index_mean'].all() > 0.0
    assert response_data['properties.index_max'].all() <= 1.0


def test_errorneous_json(mocked_client):
    response = mocked_client.post(f'/{INDEX_NAME}/raster', json={})

    assert response.status_code == 422

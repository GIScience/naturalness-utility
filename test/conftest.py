from typing import Tuple
from unittest.mock import patch

import numpy as np
import pytest
from starlette.testclient import TestClient

from app.api import app, Settings
from app.route.common import Aggregation
from naturalness.imagery_store_operator import ImageryStore, Index


class TestImageryStore(ImageryStore):
    def imagery(
        self,
        index: Index,
        area_coords: Tuple[float, float, float, float],
        start_date: str,
        end_date: str,
        resolution: int = 10,
    ) -> tuple[np.ndarray, tuple[int, int]]:
        match index:
            case Index.NDVI:
                return np.random.uniform(0.0, 1.0, (93, 100)).astype(np.float32), (93, 100)
            case Index.WATER:
                return np.random.choice([0, 1], (93, 100)).astype(np.uint8), (93, 100)
            case _:
                raise ValueError(f'Unsupported index {index}')


@pytest.fixture
def mocked_client() -> TestClient:
    with patch(
        'app.api.Settings', return_value=Settings(sentinelhub_api_id='no_id', sentinelhub_api_secret='no_secret')
    ):
        client = TestClient(app)
        app.state.imagery_store = TestImageryStore()

        yield client


@pytest.fixture
def default_vector_request() -> dict:
    return {
        'body': {
            'area_coords': [0, 0, 2, 2],
            'end_date': '2023-06-01',
        },
        'aggregation_stats': [Aggregation.max],
        'vectors': {
            'type': 'FeatureCollection',
            'features': [
                {
                    'type': 'Feature',
                    'properties': {},
                    'geometry': {
                        'type': 'Polygon',
                        'coordinates': [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
                    },
                }
            ],
        },
    }

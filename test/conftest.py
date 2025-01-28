from typing import Tuple
from unittest.mock import patch

import geojson_pydantic
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
        bbox: Tuple[float, float, float, float],
        start_date: str,
        end_date: str,
        resolution: int = 10,
    ) -> tuple[np.ndarray, tuple[int, int]]:
        if None in (index, bbox, start_date, end_date, resolution):
            raise ValueError('Missing input parameters')

        match index:
            case Index.NDVI:
                return np.array([[0.0, 0.5, 1.0], [-999.0, 1.0, 1.0]], dtype=np.float32), (2, 3)
            case Index.WATER:
                return np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]]), (2, 3)
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
def default_vector_request(default_feature_collection) -> dict:
    return {
        'time_range': {'end_date': '2023-06-01'},
        'aggregation_stats': [Aggregation.max],
        'vectors': default_feature_collection.model_dump(mode='json'),
    }


@pytest.fixture
def default_feature_collection() -> geojson_pydantic.FeatureCollection:
    return geojson_pydantic.FeatureCollection.model_validate(
        {
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
        }
    )

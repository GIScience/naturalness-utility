from datetime import datetime, timedelta

import numpy as np

from app.route.common import RemoteSensingResult
from app.route.imagery import __provide_raster
from test.app.test_api import TestImageryStore


def test_provide_raster():
    expected_result = RemoteSensingResult(
        index_data=np.array(True), height=93, width=100, area_coords=(0.0, 0.0, 1.0, 1.0)
    )

    bbox = (0.0, 0.0, 1.0, 1.0)
    imagery_store = TestImageryStore()
    computed_remote_sensing_result = __provide_raster(
        bbox=bbox, imagery_store=imagery_store, start_date=datetime.now() - timedelta(days=7), end_date=datetime.now()
    )

    assert computed_remote_sensing_result.index_data.shape == (expected_result.height, expected_result.width)
    assert computed_remote_sensing_result.width == expected_result.width
    assert computed_remote_sensing_result.height == expected_result.height

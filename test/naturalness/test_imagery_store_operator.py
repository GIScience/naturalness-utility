import tempfile
from pathlib import Path
from typing import Tuple

import numpy as np
import pytest
from sentinelhub import DataCollection, DownloadRequest, MimeType, SentinelHubRequest, BBox
from sentinelhub.constants import CRS
from sentinelhub.download.models import DownloadResponse

from app.api import Settings
from naturalness.imagery_store_operator import SentinelHubOperator, OutputFormat, Index


def test_documented_pu_calculation_example_change_detection():
    """
    This example computation is given as a reference on
    https://docs.sentinel-hub.com/api/latest/api/overview/processing-unit/. We cannot yet factor in orthorectification
    so the value tested here is 1/2 the value in the documentation.
    """
    pu = SentinelHubOperator._calculate_pus(
        width=1024,
        height=1024,
        band_number=4,
        output_format=OutputFormat.BIT_32,
        n_samples=2,
        local_collections={DataCollection.SENTINEL2_L2A},
        remote_collections=set(),
    )
    np.testing.assert_almost_equal(actual=pu, desired=21.3333333)


def test_documented_pu_calculation_example_ndvi():
    """
    This example computation is given as a reference on
    https://docs.sentinel-hub.com/api/latest/api/overview/processing-unit/ It is unclear why the example uses
    a 16 bit output format for NDVI (which is normally floating point -1..1).
    """
    pu = SentinelHubOperator._calculate_pus(
        width=20,
        height=20,
        band_number=2,
        output_format=OutputFormat.BIT_16,
        n_samples=1,
        local_collections={DataCollection.SENTINEL2_L2A},
        remote_collections=set(),
    )
    np.testing.assert_almost_equal(actual=pu, desired=0.0066666)


def test_documented_pu_calculation_1():
    """
    According to the documentation https://docs.sentinel-hub.com/api/latest/api/overview/processing-unit/ the here used
    parameters should create a PU usage of 1.0
    """
    pu = SentinelHubOperator._calculate_pus(
        width=512,
        height=512,
        band_number=3,
        output_format=OutputFormat.BIT_8,
        n_samples=1,
        local_collections={DataCollection.SENTINEL2_L2A},
        remote_collections=set(),
    )
    np.testing.assert_almost_equal(actual=pu, desired=1.0)


def test_documented_pu_calculation_min():
    """
    According to the documentation https://docs.sentinel-hub.com/api/latest/api/overview/processing-unit/ there is a
    minimum value of 0.005
    """
    pu = SentinelHubOperator._calculate_pus(
        width=1,
        height=1,
        band_number=1,
        output_format=OutputFormat.BIT_8,
        n_samples=1,
        local_collections={DataCollection.SENTINEL2_L2A},
        remote_collections=set(),
    )
    np.testing.assert_almost_equal(actual=pu, desired=0.005)


def test_pu_calculation_benchmark():
    """
    This is an actual value resulting from a real world calculation. For more information see
    `test_pu_estimation_benchmark`.

    Assuming the pu-calculation code is kept in synch with the eval script and the other code, this value is our
    benchmark that we try to minimise.
    """
    pu = SentinelHubOperator._calculate_pus(
        width=73,
        height=111,
        band_number=3,
        output_format=OutputFormat.BIT_32,
        n_samples=4,
        local_collections={DataCollection.SENTINEL2_L2A},
        remote_collections=set(),
    )
    np.testing.assert_almost_equal(actual=pu, desired=0.2472839356)


def test_pu_estimation_benchmark(responses):
    """The following input to the raster end-point

    ```json
    {
        "time_range": {
            "start_date": "2024-09-01",
            "end_date": "2024-09-10"
        },
        "bbox": [8.70,49.41,8.71,49.42]
    }
    ```

    will lead to the here described estimation variables.
    """
    operator = SentinelHubOperator(
        api_id='api_id', api_secret='api_secret', script_path=Path('conf/eval_scripts'), cache_dir=Path('/tmp')
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        responses.post(
            'https://services.sentinel-hub.com/auth/realms/main/protocol/openid-connect/token',
            json={'access_token': 'foo', 'expires_in': '99999999'},
        )
        responses.post(
            'https://services.sentinel-hub.com/api/v1/catalog/1.0.0/search',
            json={
                'context': {'next': None},
                'features': [
                    {'type': 'Feature', 'properties': {'datetime': '2024-09-02'}},
                    {'type': 'Feature', 'properties': {'datetime': '2024-09-05'}},
                    {'type': 'Feature', 'properties': {'datetime': '2024-09-07'}},
                    {'type': 'Feature', 'properties': {'datetime': '2024-09-09'}},
                ],
            },
        )
        request = SentinelHubRequest(
            data_folder=tmpdir,
            evalscript='',
            input_data=[
                SentinelHubRequest.input_data(
                    data_collection=DataCollection.SENTINEL2_L2A,
                    time_interval=('2024-09-01', '2024-09-10'),
                ),
            ],
            responses=[
                SentinelHubRequest.output_response(identifier=Index.NDVI, response_format=MimeType.TIFF),
            ],
            bbox=BBox(
                bbox=(8.70, 49.41, 8.71, 49.42),
                crs=CRS('EPSG:4326'),
            ),
            size=(73, 111),
        )
        pu_estimate = operator.estimate_pus(index=Index.NDVI, request=request)
    np.testing.assert_almost_equal(actual=pu_estimate.estimated, desired=0.247283936)


def test_pu_estimation_cached():
    operator = SentinelHubOperator(
        api_id='api_id', api_secret='api_secret', script_path=Path('conf/eval_scripts'), cache_dir=Path('/tmp')
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        cached_file = Path(f'{tmpdir}/20c3eecdfe5bdcdc3d922897317aecaa/response.tiff')
        cached_file.mkdir(parents=True)

        request = SentinelHubRequest(
            data_folder=tmpdir,
            evalscript='',
            input_data=[
                SentinelHubRequest.input_data(
                    data_collection=DataCollection.SENTINEL2_L2A,
                    time_interval=('2024-09-01', '2024-09-10'),
                ),
            ],
            responses=[
                SentinelHubRequest.output_response(identifier=Index.NDVI, response_format=MimeType.TIFF),
            ],
            bbox=BBox(
                bbox=(8.70, 49.41, 8.71, 49.42),
                crs=CRS('EPSG:4326'),
            ),
            size=(73, 111),
        )
        pu_estimation = operator.estimate_pus(index=Index.NDVI, request=request)
    assert pu_estimation.estimated == 0.0


def test_uncached_result_get_actual_pus():
    operator = SentinelHubOperator(
        api_id='api_id', api_secret='api_secret', script_path=Path('conf/eval_scripts'), cache_dir=Path('/tmp')
    )
    data = DownloadResponse(
        request=DownloadRequest(
            url='https://test.com/api/v1/endpoint',
        ),
        content=b'',
        headers={
            'x-processingunits-spent': '11.06396484375',
        },
    )
    actual_pus = operator._get_actual_pus(data=data)
    np.testing.assert_almost_equal(actual=actual_pus, desired=11.06396484375)


@pytest.mark.external
@pytest.mark.parametrize(
    'index, result_stats, pus',
    [
        (Index.NDVI, (-0.429441, 0.168175, 0.693002, 0.863718, 0.925646), 0.247283936),
        (Index.WATER, (0, 0, 0, 0, 1), 0.041213989),
        (Index.NATURALNESS, (0.0, 0.308331, 0.840473, 0.883342, 1.0), 0.247283936),
    ],
)
def test_pu_consumption_on_live_call(index: Index, result_stats: Tuple[float, float, float, float], pus: float):
    """This test asserts that the PU consumption for the provided scripts is in line with the expectations.

    This test does a live call to sentinelhub. The result is cached, but will be ignored, if the input parameters
    for the SentinelHubRequest change. In this case the test will fail in CI and you have to re-compute it locally with
    your sentinelhub credentials. To do so add @pytest.mark.withoutresponses to be able to bypass the responses which
    are automatically activated: https://github.com/getsentry/pytest-responses ;
    https://github.com/getsentry/pytest-responses/issues/5
    """
    # the settings must be provided in an .env file or as env vars by the programmer that recreates the cashed data
    # also make sure to delete old cache data
    # noinspection PyArgumentList
    settings = Settings()
    operator = SentinelHubOperator(
        api_id=settings.sentinelhub_api_id,
        api_secret=settings.sentinelhub_api_secret,
        script_path=Path('conf/eval_scripts'),
        cache_dir=Path('test/resources/sentinelhub_cache'),
    )
    raster_output = operator.imagery(
        index=index, bbox=(8.70, 49.41, 8.71, 49.42), start_date='2024-09-01', end_date='2024-09-10'
    )

    np.testing.assert_array_almost_equal(
        actual=np.nanpercentile(raster_output.index_data, (0, 25, 50, 75, 100)), desired=result_stats
    )
    np.testing.assert_almost_equal(actual=raster_output.pus.consumed, desired=pus)

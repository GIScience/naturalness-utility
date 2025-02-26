import tempfile
from pathlib import Path

import numpy.testing
from sentinelhub import DataCollection, DownloadRequest, MimeType, SentinelHubRequest, BBox
from sentinelhub.constants import CRS
from sentinelhub.download.models import DownloadResponse

from naturalness.imagery_store_operator import SentinelHubOperator, OutputFormat, Index


def test_pu_calculation_change_detection():
    """

    This example computation is given as a reference on
    https://docs.sentinel-hub.com/api/latest/api/overview/processing-unit/. We cannot yet factor in orthorectification
    so you value is 1/2 the value in the documentation.
    """
    pu = SentinelHubOperator._calculate_pus(
        width=1024,
        height=1024,
        band_number=4,
        output_format=OutputFormat.BIT_32,
        n_samples=2,
        local_collections={DataCollection.SENTINEL2_L2A},
        remote_collections=set(),
        eval_script_duration=200,
    )
    numpy.testing.assert_almost_equal(actual=pu, desired=21.3333333)


def test_pu_calculation_ndvi():
    """

    This example computation is given as a reference on
    https://docs.sentinel-hub.com/api/latest/api/overview/processing-unit/
    """
    pu = SentinelHubOperator._calculate_pus(
        width=20,
        height=20,
        band_number=2,
        output_format=OutputFormat.BIT_8,
        n_samples=1,
        local_collections={DataCollection.SENTINEL2_L2A},
        remote_collections=set(),
        eval_script_duration=200,
    )
    numpy.testing.assert_almost_equal(actual=pu, desired=0.0066666)


def test_pu_calculation_ndvi_slow():
    """Same as pu calculation test above, but assuming slow return to test that branch of code."""
    pu = SentinelHubOperator._calculate_pus(
        width=20,
        height=20,
        band_number=2,
        output_format=OutputFormat.BIT_8,
        n_samples=1,
        local_collections={DataCollection.SENTINEL2_L2A},
        remote_collections=set(),
        eval_script_duration=201,
    )
    numpy.testing.assert_almost_equal(actual=pu, desired=0.0099999)


def test_pu_calculation_benchmark():
    """
    This is an actual value resulting from a real world calculation. All values are fixed except the eval-script
    duration that is yet not clear how it comes to live. For more information see `test_pu_estimation_benchmark`.

    Assuming the pu-calculation code is kept in synch with the eval script and the other code, this value is our
    benchmark that we try to minimise.
    """
    pu = SentinelHubOperator._calculate_pus(
        width=332,
        height=364,
        band_number=2,
        output_format=OutputFormat.BIT_8,
        n_samples=6,
        local_collections={DataCollection.SENTINEL2_L2A},
        remote_collections=set(),
        eval_script_duration=1200,
    )
    numpy.testing.assert_almost_equal(actual=pu, desired=11.06396484375)


def test_pu_estimation_benchmark():
    """The following input to the raster end-point

    ```json
    {
        "time_range": {
            "end_date": "2024-07-07",
            "start_date": "2024-06-08"
        },
        "bbox": [
            8.70,
            49.38,
            8.75,
            49.41
        ]
    }
    ```

    will lead to the here described estimation variables.

    The actual PU value for this computation was 11.06396484375 (see `test_pu_calculation_benchmark`) meaning an
    eval_return time between 1101 and 1200.
    """
    operator = SentinelHubOperator(
        api_id='api_id', api_secret='api_secret', script_path=Path('conf/eval_scripts'), cache_dir=Path('/tmp')
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        request = SentinelHubRequest(
            data_folder=tmpdir,
            evalscript='',
            input_data=[
                SentinelHubRequest.input_data(
                    data_collection=DataCollection.SENTINEL2_L2A,
                    time_interval=('2024-06-08', '2024-07-07'),
                ),
            ],
            responses=[
                SentinelHubRequest.output_response(identifier=Index.NDVI, response_format=MimeType.TIFF),
            ],
            bbox=BBox(
                bbox=(8.70, 49.38, 8.75, 49.41),
                crs=CRS('EPSG:4326'),
            ),
            size=(332, 364),
        )
        pu_lower_estimate, pu_upper_estimate = operator.estimate_pus(
            index=Index.NDVI, request=request, eval_duration_range=(1100, 1300)
        )
    numpy.testing.assert_almost_equal(actual=pu_lower_estimate, desired=10.1419677734375)
    numpy.testing.assert_almost_equal(actual=pu_upper_estimate, desired=11.9859619140625)


def test_pu_estimation_cached():
    operator = SentinelHubOperator(
        api_id='api_id', api_secret='api_secret', script_path=Path('conf/eval_scripts'), cache_dir=Path('/tmp')
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        cached_file = Path(f'{tmpdir}/f68d39a21aa024ce5ccca56ed6035ef0/response.tiff')
        cached_file.mkdir(parents=True)
        request = SentinelHubRequest(
            data_folder=tmpdir,
            evalscript='',
            input_data=[
                SentinelHubRequest.input_data(
                    data_collection=DataCollection.SENTINEL2_L2A,
                    time_interval=('2024-06-08', '2024-07-07'),
                ),
            ],
            responses=[
                SentinelHubRequest.output_response(identifier=Index.NDVI, response_format=MimeType.TIFF),
            ],
            bbox=BBox(
                bbox=(8.70, 49.38, 8.75, 49.41),
                crs=CRS('EPSG:4326'),
            ),
            size=(332, 364),
        )
        pu_lower_estimate, pu_upper_estimate = operator.estimate_pus(
            index=Index.NDVI, request=request, eval_duration_range=(1100, 1300)
        )
    assert pu_lower_estimate == 0.0
    assert pu_upper_estimate == 0.0


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
    actual_pus = operator._get_actual_pus(data=data, min_estimated_pus=10.0, max_estimated_pus=100.0)
    numpy.testing.assert_almost_equal(actual=actual_pus, desired=11.06396484375)


def test_cached_result_get_actual_pus():
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
    actual_pus = operator._get_actual_pus(data=data, min_estimated_pus=0.0, max_estimated_pus=0.0)
    assert actual_pus == 0.0

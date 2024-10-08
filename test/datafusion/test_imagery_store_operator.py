from pathlib import Path
import configobj
import numpy as np
from datafusion.imagery_store_operator import SentinelHubOperator


# load SentinelHub API credentials and settings
config = configobj.ConfigObj('.env')
api_id = config['SENTINELHUB_API_ID']
api_secret = config['SENTINELHUB_API_SECRET']

cache_dir = Path('./.cache_tst')
area_coords = [7.38, 47.51, 7.39, 47.52]
start_date = '2023-05-01'
end_date = '2023-05-15'
resolution = 10
evalscript_name = 'ndvi_evalscript'  # TODO parametrizes this later with evalscript specific for planet
index_name = 'ndvi'


def test_imagery():
    imagery, imagery_size = SentinelHubOperator(api_id, api_secret, index_name, evalscript_name, cache_dir).imagery(
        area_coords, start_date, end_date, resolution
    )
    assert imagery_size == (110, 78)
    assert (
        np.all((imagery >= 0.0) & (imagery <= 1.0) | np.isnan(imagery)).sum() == 1
    )  # all NDVI values should be between [0,1] or nan

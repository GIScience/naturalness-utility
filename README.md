# Naturalness-utility

Small utility with the functionality to return spectral indices (e.g. the NDVI) derived from remote sensing data (e.g. Sentinel-2 or Planet imagery). The utility can be used by other utilitlies, such as for walkability and bikeability.

The structure of this project is similar to the `lulc-utility`, such as similar example AOI, same configuration of pre-commit hooks and Continuous Integration

**Note** A poetry environment is used, initalize the environment via `poetry install`  which installs all dependencies from `poetry.lock` file


## Indices


### NDVI
The aim is to calculate the urban naturalness, e.g. along streets. Thus, the maximum NDVI is returned by API endpoints as a raster- and vector-based calculation of the greenness. The AOI and timespan can be defined by the user as well as the input vector data (`geojson`). This `geojson` file is used to aggregate the NDVI (from the raster file) based on an user-defined vector (Point, Line, Polygon). \
The aggregated vector file (`json`), returned from the API, contains zonal statistics of the index (e.g. NDVI), while the returned raster file (`tiff`) is a scene of the maximum NDVI for the given time and area.\
A template of the `geojson` file can be found here: `./test/test_data/test_vector.geojson`.


### Further indices
...


## Development
Note that the repository supports pre commit hooks defined in the `.pre-commit-config.yaml` file.
For the description of each hook visit the documentation of:

- git pre-commit hooks
- ruff pre-commit hooks

Run `poetry run pre-commit install` to activate them.


## Run
- Set project root as working directory: `export PYTHONPATH="datafusion:$PYTHONPATH"`
- Setup your credentials in `.env`
- Query the maximum NDVI as imagery its zonal statistics for a default AOI and time span: `python app/api.py`


## Docker
The tool is also Dockerised. To start it, run the following commands
```
docker build . --tag heigit/datafusion:devel
docker run --publish 8000:8000  --env-file .env heigit/datafusion:devel
```


Then head to the link above. Populate the .env file using the .env_template.


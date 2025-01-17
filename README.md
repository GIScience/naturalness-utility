# Naturalness-utility

Small utility with the functionality to return spectral indices (e.g. the NDVI) derived from remote sensing data.

The structure of this project is similar to
the [LULC Utility](https://gitlab.heigit.org/climate-action/utilities/lulc-utility).

## Indices

### NDVI

The utility returns the maximum NDVI over a user defined time period within a user defined area as GeoTiff raster via
the `raster` endpoint.
In addition, an aggregation of NDVI values to simple feature geometries is possible via the `vector`-endpoint.

## Development

## Setup

[Poetry](https://python-poetry.org/) is used as dependency management.
Initalize the environment via `poetry install`  which installs all dependencies from `poetry.lock` file.

Note that the repository supports pre commit hooks defined in the `.pre-commit-config.yaml` file.
Run `poetry run pre-commit install` to activate them.

## Run

- Set project root as working directory: `export PYTHONPATH="naturalness:$PYTHONPATH"`
- Copy the [.env_template](.env_template) file to `.env` and add the required credentials
- Run`python app/api.py` to start the utility

## Docker

The tool is also Dockerised.
To start it, run the following commands

```
docker build . --tag repo.heigit.org/climate-action/naturalness:devel
docker run --publish 8000:8000  --env-file .env repo.heigit.org/climate-action//naturalness:devel
```

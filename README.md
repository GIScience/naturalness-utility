# Naturalness-utility

Small utility with the functionality to return spectral indices (e.g. the NDVI) derived from remote sensing data.

The structure of this project is similar to
the [LULC Utility](https://gitlab.heigit.org/climate-action/utilities/lulc-utility).

## Indices

### NDVI

The utility returns the median NDVI [-1.0,1.0] over a user defined time period within a user defined area as GeoTiff
raster via the `raster` endpoint.
In addition, an aggregation of NDVI values to SimpleFeature geometries is possible via the `vector`-endpoint.

### WATER

Returns a basic water mask derived from the
Sentinel [Scene Classification Map (SCL)](https://custom-scripts.sentinel-hub.com/custom-scripts/sentinel-2/scene-classification/).
A value of 1 depicts areas covered by water in most of the images from the time range looked at.

### NATURALNESS

This is a combination of NDVI and WATER that sets the output value to 1.0 for water-pixels.

## Development

## Setup

[Poetry](https://python-poetry.org/) is used as dependency management.
Initalize the environment via `poetry install`  which installs all dependencies from `poetry.lock` file.

Note that the repository supports pre commit hooks defined in the `.pre-commit-config.yaml` file.
Run `poetry run pre-commit install` to activate them.

## Run

- Copy the [.env_template](.env_template) file to `.env` and add the required credentials
- Run `poetry run python app/api.py` to start the utility

## Docker

The tool is also Dockerised.
To start it, run the following commands

```
docker build . --tag repo.heigit.org/climate-action/naturalness:devel
docker run --rm --publish 8000:8000  --env-file .env repo.heigit.org/climate-action/naturalness:devel
```

## Releasing a new utility version

1. Update the [CHANGELOG.md](CHANGELOG.md).
   It should already be up to date but give it one last read and update the heading above this upcoming release
2. Decide on the new version number.
   Please adhere to the [Semantic Versioning](https://semver.org/) scheme, based on the changes since the last release.
3. Update the version attribute in the [pyproject.toml](pyproject.toml) (e.g. by running
   `poetry version {patch|minor|major}`)
4. Create a [release]((https://docs.gitlab.com/ee/user/project/releases/#create-a-release-in-the-releases-page)) on
   GitLab, including a changelog


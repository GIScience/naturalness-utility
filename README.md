# RS-indices-utility

Small utility with the functionality to return different indices, such as the NDVI, from remote sensing data, such as Sentinel or from planet. The utility can be used by other utilitlies, such as for walkability and bikeability.\


The structure of this project is similar to the `lulc-utility`, such as similar example AOI, same configuration of pre-commit hooks and Continuous Integration

**Note** A poetry environment is used, initalize the environment via `poetry install`  which installs all dependencies from `poetry.lock` file

## Indices


### NDVI

For now the maximum NDVI is returned as a raster file by an API endpoint, based on user-defined AOI and timespan. In the near future a further endpoint will be added which provides a vectorized version of the NDVI cropped with OSM data. The aim is to calculate the urban greenness e.g. along streets.


### Further indices
...


## Development
Note that the repository supports pre commit hooks defined in the `.pre-commit-config.yaml` file.
For the description of each hook visit the documentation of:

- git pre-commit hooks
- ruff pre-commit hooks

Run `poetry run pre-commit install` to activate them.


## Run
Set project root as working directory: `export PYTHONPATH="datafusion:$PYTHONPATH"`

...


## Docker
The tool is also Dockerised. To start it, run the following commands
```
docker build . --tag heigit/datafusion:devel
docker run --publish 8000:8000  --env-file .env heigit/datafusion:devel
```


Then head to the link above. Populate the .env file using the .env_template.



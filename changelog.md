# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project mostly adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [Unreleased](https://gitlab.heigit.org/climate-action/utilities/naturalness-utility)

### Added

- first version of a Remote-Sensing Utility
- API functionality with client-input parameters to define AOI and time span for which an indice is calculated ([#4](https://gitlab.heigit.org/climate-action/utilities/naturalness-utility/-/issues/4))
    - currently one indice (max. NDVI) using sentinel 2 imageries is implemented
    - API endpoint returns indice (max. NDVI) as `raster` file
    - health- and functionality-tests for the API
- docker build ([#2](https://gitlab.heigit.org/climate-action/utilities/naturalness-utility/-/issues/2), [#3](https://gitlab.heigit.org/climate-action/utilities/naturalness-utility/-/issues/3))
- CI and pre-commit hooks ([#2](https://gitlab.heigit.org/climate-action/utilities/naturalness-utility/-/issues/2), [#3](https://gitlab.heigit.org/climate-action/utilities/naturalness-utility/-/issues/3))


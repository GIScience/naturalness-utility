# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project mostly adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://gitlab.heigit.org/climate-action/utilities/naturalness-utility/-/compare/9418a2030dd3ecf312f80ea055d6fc133fc1445d...main)

### Added

- first version of a Naturalness Utility
- API functionality with client-input parameters to define AOI and time span for which an index is
  calculated ([#4](https://gitlab.heigit.org/climate-action/utilities/naturalness-utility/-/issues/4))
    - currently one index (max. NDVI) based on Sentinel-2 imagery is implemented
    - API endpoints return an index (max. NDVI) as a `raster` file and
    - its zonal statistics aggregate the given index for the geometries in the user-provided FeatureCollection


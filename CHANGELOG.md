# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project mostly adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://gitlab.heigit.org/climate-action/utilities/naturalness-utility/-/compare/1.0.0...main)

### Fixed

- removed the trailing slash in the `/health` route ([infrastructure#55](https://gitlab.heigit.org/climate-action/infrastructure/-/issues/55))

### Added

- the utility is now able to estimate the required PUs and retrieve the actually consumed PUs

## [1.0.0](https://gitlab.heigit.org/climate-action/utilities/naturalness-utility/-/releases/1.0.0) - 2025-01-28

### Added

- first version of a Naturalness Utility: API functionality with client-input parameters to define AOI and time span for
  which an index is calculated ([#4](https://gitlab.heigit.org/climate-action/utilities/naturalness-utility/-/issues/4))
    - currently three indices (median NDVI, water, combination of both called naturalness) based on Sentinel-2 imagery
      are implemented
    - API endpoints return an index as a `raster` file and
    - its zonal statistics aggregate the given index for the geometries in the user-provided FeatureCollection using
      user-provided metrics


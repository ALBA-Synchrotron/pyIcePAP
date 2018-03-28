# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]

<!-- ## [2.0.0] - 2018-??-?? -->
<!-- For a full log of commits between versions run (in your git repo): -->
<!-- `git log 1.22.0..2.0.0` -->

### Added
- New library implementation API v2.0. Splits the base classes in three new modules: `communiction`, `controller` and `axis`.
- Support for `Electronic CAM` (ECAM) configuration.
- Support for programming mode (firmware management).
- Support to `parametric` and `tracking` trajectories (PMUX, SYNCRES and TRACK commands).
- Support to `auxiliar configuration line` (SYNCAUX).
- Library and application loggers based on logging module.
- New `firmware update` application.
- New `icepap backup` application.
- ESRF data vector library.
- Distribution based on [setuptools](https://setuptools.readthedocs.io/en/latest/#).
- Automatic documentation based on [sphinx](http://www.sphinx-doc.org/en/1.5.1/index.html).
- GPL+v3 license.
- `flake8` configuration file.
- `travis` configuration file.

### Deprecated
- Old API implementation moved to legacy module.

### Removed
- Support for ipython profile.

## [1.22.0] - 2015-05-29
Last Release of pyIcePAP library.

[keepachangelog.com]: http://keepachangelog.com
[Unreleased]: https://github.com/ALBA-Synchrotron/pyIcePAP/compare/1.22.0...HEAD
[1.22.0]: https://github.com/ALBA-Synchrotron/pyIcePAP/tree/1.22.0

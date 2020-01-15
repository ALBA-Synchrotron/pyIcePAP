# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

<!--## [Unreleased] -->
<!--### Added -->

## [3.2.X] 
### Added
 - Allow to force the posicion/encoder register on the autofix script from
  the backup file.
 - Allow to skip register by the user on the autofix script. 

### Removed

### Fixed


## [3.1.0] 
### Added
 - Allow to do not pass polarity for commands: infoX, outpos, outpaux, syncpos 
 and syncaux

### Removed

### Fixed


## [3.0.1] 

### Added
- Migrate to python 3.5: Methods will return 'int' instead of 'long'
- Rename module to "icepap". 
- Add IcePAPController and IcePAPCommunication classes.
- Allow to use the controller without axes created by default. 
- Add more test cases.
- Configure travis to run the test cases.
- Add requirements to build the documentation
 
### Removed
- Remove serial communication and support only ethernet communication.
- Remove EthIcePAPController and EthIcePAPCommunication classes.
- Remove deprecated method.
- Remove legacy module (API 1.X).
- Remove ipython script.

### Fixed
- Return a string instead of list on Mode property.
- Fix mistake on the name of 'verserr' axis method.
- Fix error on get_indexer_str.
- Fix documentation. 
- Fix installation requirements.


## [2.9.0] 

### Added
- Optimize EthIcePAPController to do not create unused axes. 
- Allow to create axes on execution time. 
- Allow to use the controller without axes created. 
- Add testing scripts. 

### Fixed
- Remove version checking on the update script.  

## [2.8.1] 

### Added
- Add axes and drivers as controller properties.
 

### Fixed
- Remove to iterate over the controller and take the IcePAPAxis object as 
value, it breaks the heritage theory. It was a wrong feature introduced. 

## [2.7.2] 

### Added
- Add search methods. 

### Fixed
- Add protection when reading the axis name on the starting. 
- Add protection when reading the config. 

## [2.6.1] 

### Added
- Add status_register as property of the State class. 

### Fixed
- Bug on getting the home registers: position and encoder 

## [2.5.0] 

### Added
- Implement disconnection method used on IcepapCMS

### Fixed
- Remove the legacy module from the PEP8 verification. 

## [2.4.1] 

### Added
- Allow to read the driver PCB version as property of firmware version class.

### Fixed
- Fix errors on configuration commands when using a parameter. 

## [2.3.7] - 2018-08-28

### Added
- Allow to change the data format of the parameter, slope and motor position
 tables.

### Fixed
- Use ordered dictionaries on the configuration data. 
- Correct the return value of the get_parametric_table method.  
- Protect connection to one IcePAP OFF.
- Change autofix method used on pyIcePAP update command to do not restore 
the encoders and positions registers.
- Add protection on the firmware version reading.
- Show deprecation warnings only one time. 
- Add more descriptive filenames for configuration backups and logs.

## [2.2.0] - 2018-04-05
For a full log of commits between versions run (in your git repo):
`git log 2.0.0..2.2.0`

### Added
- Create new application command autofix: applies automatic conflict solutions after a firmware update.
- pyIcePAP application retrieves library version on request.

### Fixed
- Remove unnecessary imports and reduce configparser as dependency at the application level.
- Correct parsing when axis name requestes is sn empty string.
- Add link to documentation.
- Correct README file.
- New configuration for bumpversion.
- Protect exception on version request.
- Correct bare Exception statatement.

## [2.0.0] - 2018-03-28

### Added
- New library implementation API v2.0. Splits the base classes in three new modules: `communication`, `controller` and `axis`.
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
Last release of pyIcePAP library (old API).

[keepachangelog.com]: http://keepachangelog.com
[Unreleased]: https://github.com/ALBA-Synchrotron/pyIcePAP/compare/2.3.2...HEAD
[3.2.x]: https://github.com/ALBA-Synchrotron/pyIcePAP/compare/2.3.1...HEAD
[3.1.0]: https://github.com/ALBA-Synchrotron/pyIcePAP/compare/2.3.1...HEAD
[3.0.1]: https://github.com/ALBA-Synchrotron/pyIcePAP/compare/2.9.0...3.0.1
[2.9.0]: https://github.com/ALBA-Synchrotron/pyIcePAP/compare/2.8.1...2.9.0
[2.8.1]: https://github.com/ALBA-Synchrotron/pyIcePAP/compare/2.7.2...2.8.1
[2.7.2]: https://github.com/ALBA-Synchrotron/pyIcePAP/compare/2.6.1...2.7.2
[2.6.1]: https://github.com/ALBA-Synchrotron/pyIcePAP/compare/2.5.0...2.6.1
[2.5.0]: https://github.com/ALBA-Synchrotron/pyIcePAP/compare/2.4.1...2.5.0
[2.4.1]: https://github.com/ALBA-Synchrotron/pyIcePAP/compare/2.3.7...2.4.1
[2.3.7]: https://github.com/ALBA-Synchrotron/pyIcePAP/compare/2.2.0...2.3.7
[2.2.0]: https://github.com/ALBA-Synchrotron/pyIcePAP/compare/2.0.0...2.2.0
[2.0.0]: https://github.com/ALBA-Synchrotron/pyIcePAP/compare/1.22.0...2.0.0
[1.22.0]: https://github.com/ALBA-Synchrotron/pyIcePAP/tree/1.22.0

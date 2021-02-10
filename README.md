# icepap

![Pypi version][pypi]

Python module to configure, control and monitor IcePAP based systems.


## Installation

From within your favourite python environment:

```console
pip install icepap
```

Additionally, if you want to use `icepapctl` (the icepap CLI), you need some
extra dependencies which can be installed with:

```console
pip install icepap[cli]
```

*Note:* The CLI requires a python >= 3.6 environment.

## Usage

The icepap python library in action:

![spec in action](./demo.svg)

The icepapctl command line tool in action:

![spec in action](./icepapctl.svg)

## Documentation

The project documentation can be found [here](https://alba-synchrotron.github.io/pyIcePAP-doc) or you can build it by executing:
```console
python setup.py build_sphinx
```

This documentation has been created by [sphinx](http://www.sphinx-doc.org/en/stable/).

## Tests

You can run tests simply with:
```console
python setup.py test
```

## Contribute

You can find how to contribute to this project on CONTRIBUTING.md file.


[pypi]: https://img.shields.io/pypi/pyversions/icepap.svg

# icepap

![Pypi version][pypi]

Python module to configure, control and monitor IcePAP based systems.


## Installation

From within your favourite python environment:

```console
pip install icepap
```

icepap is also available on [conda-forge](https://github.com/conda-forge/icepap-feedstock).
You can install it using [conda](https://docs.conda.io):

```console
conda install -c conda-forge icepap
```

## Documentation

The project documentation can be build it by executing:
```console
python setup.py build_sphinx
```

This documentation has been created by [sphinx](http://www.sphinx-doc.org/en/stable/).

## Simulation
This is based on [sintruments](http://github.com/tiagocoutinho/sinstruments).
It provides simulation for basic motion including jog.

Install with:
```
$ pip install icepap[simulator]
```

Make sure icepap simulator is registered:
```
$ sinstruments-server ls
[...]
IcePAP from icepap <current version #.#.#>
[...]
```

Configure a yaml file called `ice.yaml`. Example:
```yaml
    devices:
    - class: IcePAP
      name: ipap_simu
      transports:
      - type: tcp
        url: 0:5000
      axes:
      - address: 1
        velocity: 100
        name: th
      - address: 2
        name: tth
        acctime: 0.125
      - address: 11
        name: phi
      - address: 12
        name: chi
```

run server with:
```
sinstruments-server -c ./ice.yaml --log-level=debug
```
access like a "real" icepap with this python library or from cli:
```
$ nc -C localhost 5000
1:?pos
1:?pos 0
```

## Tests

You can run tests simply with:
```console
python setup.py test
```

## Contribute

You can find how to contribute to this project on CONTRIBUTING.md file.


[pypi]: https://img.shields.io/pypi/pyversions/icepap.svg

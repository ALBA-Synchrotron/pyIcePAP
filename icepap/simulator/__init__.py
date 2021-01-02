"""
.. code-block:: yaml

    devices:
    - class: IcePAP
      package: icepap.simulator
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
"""

from .core import IcePAP

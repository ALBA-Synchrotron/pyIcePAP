import collections
import pytest
import unittest.mock as mock
import icepap

from patch_socket import mock_socket


@pytest.fixture
def smart_pap():
    """Smart IcePAP => auto_axes = True"""
    with mock_socket():
        ice = icepap.IcePAPController('icepaptest', auto_axes=True)
        yield ice


@pytest.fixture
def expert_pap():
    """Expert IcePAP => auto_axes = False"""
    with mock_socket():
        ice = icepap.IcePAPController('icepaptest', auto_axes=False)
        yield ice

import collections
import pytest
import unittest.mock as mock
import icepap

from patch_socket import patch_socket


@pytest.fixture
def smart_pap():
    """Smart IcePAP => auto_axes = True"""
    with mock.patch('icepap.communication.socket.socket') as mock_sock:
        patch_socket(mock_sock)
        ice = icepap.IcePAPController('icepaptest', auto_axes=True)
        yield ice


@pytest.fixture
def expert_pap():
    """Expert IcePAP => auto_axes = False"""
    with mock.patch('icepap.communication.socket.socket') as mock_sock:
        patch_socket(mock_sock)
        ice = icepap.IcePAPController('icepaptest', auto_axes=False)
        yield ice

import pytest

from pyIcePAP.communication import CommType
from pyIcePAP import EthIcePAPController

from patch_socket import protect_socket, patch_socket, socket_context


def confirm_initial_m1_state(s1):
    assert s1.status_register == 0x00205013
    assert s1.is_present()
    assert s1.is_alive()
    assert s1.get_mode_str() == 'OPER'
    assert s1.is_disabled()
    assert s1.get_disable_str() == 'Axis not active'


@pytest.mark.parametrize('auto_axes', [True, False], ids=['smart', 'expert'])
def test_create_eth_icepap(auto_axes):
    with socket_context() as mock_sock:
        patch_socket(mock_sock)
        with pytest.raises(RuntimeError):
            ice = EthIcePAPController('weirdhost')
        with pytest.raises(RuntimeError):
            ice = EthIcePAPController('icepap1', 5001)
        ice = EthIcePAPController('icepap1', 5000)
        assert ice is not None



@pytest.mark.parametrize('auto_axes', [True, False], ids=['smart', 'expert'])
def test_connection(auto_axes):
    with socket_context() as mock_sock:
        patch_socket(mock_sock)
        pap = EthIcePAPController('icepap1', auto_axes=auto_axes)

        assert pap.comm_type == CommType.Socket
        assert pap.connected

        pap.disconnect()
        assert not pap.connected


@pytest.mark.parametrize('auto_axes', [True, False], ids=['smart', 'expert'])
def test_system(auto_axes):
    with socket_context() as mock_sock:
        patch_socket(mock_sock)
        pap = EthIcePAPController('icepap1', auto_axes=auto_axes)

        assert pap.mode == 'OPER'

        assert pap.get_pos(1) == [55]
        assert pap.get_pos([1]) == [55]
        assert pap.get_pos([1, 5]) == [55, -3]
        assert pap.get_pos([5, 1]) == [-3, 55]

        assert pap.get_fpos(1) == [55]
        assert pap.get_fpos([1]) == [55]
        assert pap.get_fpos([1, 5]) == [55, -3]
        assert pap.get_fpos([5, 1]) == [-3, 55]

        assert pap.get_status(1) == [0x00205013]
        assert pap.get_status([1]) == [0x00205013]
        assert pap.get_status([1, 5]) == [0x00205013, 0x00205013]

        assert pap.get_fstatus(1) == [0x00205013]
        assert pap.get_fstatus([1]) == [0x00205013]
        assert pap.get_fstatus([1, 5]) == [0x00205013, 0x00205013]

        s1 = pap.get_states(1)[0]
        confirm_initial_m1_state(s1)
        assert pap.get_states([1])[0].status_register == 0x00205013
        assert [s.status_register for s in pap.get_states([1, 5])] == [
                                                                0x00205013, 0x00205013]

        assert pap.get_power(1) == [True]
        assert pap.get_power([1]) == [True]
        assert pap.get_power([1, 151]) == [True, False]
        assert pap.get_power([151, 1]) == [False, True]

        with pytest.raises(ValueError):
            pap.get_pos('th')

        pap.add_alias('th', 1)

        assert pap.get_pos('th') == [55]


@pytest.mark.parametrize('auto_axes', [True, False], ids=['smart', 'expert'])
def test_racks(auto_axes):
    with socket_context() as mock_sock:
        patch_socket(mock_sock)
        pap = EthIcePAPController('icepap1', auto_axes=auto_axes)
        assert pap.get_rid(0) == ['0008.0153.F797']
        assert pap.get_rid([0]) == ['0008.0153.F797']

        assert pap.get_rid([0, 15]) == ['0008.0153.F797', '0008.020B.1028']
        assert pap.get_rid([15, 0]) == ['0008.020B.1028', '0008.0153.F797']

        assert pap.get_rtemp(0) == [30.1]
        assert pap.get_rtemp([0]) == [30.1]

        assert pap.get_rtemp([0, 15]) == [30.1, 29.5]
        assert pap.get_rtemp([15, 0]) == [29.5, 30.1]


def test_smart_axis(smart_pap):
    assert 1 in smart_pap
    assert 'th' not in smart_pap
    assert len(smart_pap.axes) == 3
    assert set(smart_pap.axes) == {1, 5, 151}

    drivers = smart_pap.drivers

    assert len(drivers) == 3

    with pytest.raises(ValueError):
        smart_pap[200]

# BUG in pyicepap: Does not raise error
#    with pytest.raises(ValueError):
#        smart_pap[2]

    with pytest.raises(ValueError):
        smart_pap['m1']

    m1 = smart_pap[1]

    assert m1 in drivers

    smart_pap.add_alias('toto', 1)
    assert len(drivers) == 3
    toto = smart_pap['toto']
    assert m1 is toto

    assert m1.addr == 1
    assert m1.name == 'th'
    assert m1.pos == 55
    assert m1.status == 0x00205013
    assert m1.power == True
    s1 = m1.state
    confirm_initial_m1_state(s1)

    assert smart_pap.get_pos(1) == [55]
    assert smart_pap.get_pos('toto') == [55]

    del smart_pap[1]
    assert 1 not in smart_pap


def test_smart_find_axes(smart_pap):
    assert set(smart_pap.find_axes()) == {1, 5, 151, 152}
    assert set(smart_pap.find_axes(only_alive=True)) == {1, 5, 151}


def test_smart_update_axes(smart_pap):
    m1 = smart_pap[1]
    smart_pap.update_axes()
    assert m1 is smart_pap[1]


def test_expert_axis(expert_pap):
    assert 1 not in expert_pap
    assert 'th' not in expert_pap
    assert len(expert_pap.axes) == 0

    m1 = expert_pap[1]

    assert 1 in expert_pap

    assert len(expert_pap.axes) == 1
    assert set(expert_pap.axes) == {1}

    drivers = expert_pap.drivers

    assert len(expert_pap.drivers) == 1

    with pytest.raises(ValueError):
        expert_pap[200]

    with pytest.raises(ValueError):
        expert_pap['m1']

    expert_pap.add_alias('toto', 1)
    assert len(drivers) == 1
    toto = expert_pap['toto']
    assert m1 is toto

    assert m1.addr == 1
    assert m1.name == 'th'
    assert m1.pos == 55
    assert m1.status == 0x00205013
    assert m1.power == True
    s1 = m1.state
    confirm_initial_m1_state(s1)

    assert expert_pap.get_pos(1) == [55]
    assert expert_pap.get_pos('toto') == [55]

    del expert_pap[1]
    assert 1 not in expert_pap


def test_expert_find_axes(expert_pap):
    assert len(expert_pap.axes) == 0
    assert set(expert_pap.find_axes()) == {1, 5, 151, 152}
    assert set(expert_pap.find_axes(only_alive=True)) == {1, 5, 151}
    assert len(expert_pap.axes) == 0


def test_expert_update_axes(expert_pap):
    m1 = expert_pap[1]
    expert_pap.update_axes()
    assert 1 in expert_pap
    assert 5 not in expert_pap
    assert m1 is expert_pap[1]

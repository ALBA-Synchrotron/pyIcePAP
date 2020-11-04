import pytest
import random

from icepap import IcePAPController

from patch_socket import mock_socket


def get_random_pos():
    return random.randrange(-10000, 10000)


def confirm_m1(m1):
    # Status register 0x00205013
    assert m1.state_present is True
    assert m1.state_moving is False
    assert m1.state_ready is False
    assert m1.state_settling is False
    assert m1.state_outofwin is True
    assert m1.state_warning is False
    assert m1.state_alive is True
    assert m1.state_mode_str == 'OPER'
    assert m1.state_mode_code == 0
    assert m1.state_disabled is True
    assert m1.state_disable_code == 1
    assert m1.state_disable_str == 'Axis not active'
    assert m1.state_indexer_code == 0
    assert m1.state_indexer_str == 'Internal indexer'
    assert m1.state_stop_code == 1
    assert m1.state_stop_str == 'Stop'
    assert m1.state_limit_positive is False
    assert m1.state_limit_negative is False
    assert m1.state_inhome is False
    assert m1.state_5vpower is True
    assert m1.state_verserr is False
    assert m1.state_poweron is False
    assert m1.state_info_code == 0

    assert m1.stopcode == 0
    assert m1.vstopcode == 'No abnormal stop condition'
    assert m1.active is True
    assert m1.mode == 'OPER'
    assert m1.alarm == (False, '')
    assert m1.config == 'toto@pc1_2019/06/17_12:51:24'
    assert m1.id == ('0008.028E.EB82', '4960')

    assert m1.meas_vcc == 80.2165
    assert m1.meas_i == 0.00545881
    assert m1.meas_ia == -0.00723386
    assert m1.meas_ib == -0.000653267
    assert m1.meas_ic == 0
    assert m1.meas_r == -6894.35
    assert m1.meas_ra == -3797.74
    assert m1.meas_rb == -3797.74
    with pytest.raises(RuntimeError):
        m1.meas_rc

    pos = get_random_pos()
    m1.pos = pos
    assert m1.pos == pos
    pos = get_random_pos()
    m1.pos_shftenc = pos
    assert m1.pos_shftenc == pos
    pos = get_random_pos()
    m1.pos_tgtenc = pos
    assert m1.pos_tgtenc == pos
    pos = get_random_pos()
    m1.pos_ctrlenc = pos
    assert m1.pos_ctrlenc == pos
    pos = get_random_pos()
    m1.pos_encin = pos
    assert m1.pos_encin == pos
    pos = get_random_pos()
    m1.pos_inpos = pos
    assert m1.pos_inpos == pos
    # TODO implement exception to configuration mode
    pos = get_random_pos()
    m1.pos_absenc = pos
    assert m1.pos_absenc == pos
    pos = get_random_pos()
    m1.pos_motor = pos
    assert m1.pos_motor == pos
    pos = get_random_pos()
    m1.pos_sync = pos
    assert m1.pos_sync == pos

    pos = get_random_pos()
    m1.enc = pos
    assert m1.enc == pos
    pos = get_random_pos()
    m1.enc_shftenc = pos
    assert m1.enc_shftenc == pos
    pos = get_random_pos()
    m1.enc_tgtenc = pos
    assert m1.enc_tgtenc == pos
    pos = get_random_pos()
    m1.enc_ctrlenc = pos
    assert m1.enc_ctrlenc == pos
    pos = get_random_pos()
    m1.enc_encin = pos
    assert m1.enc_encin == pos
    pos = get_random_pos()
    m1.enc_inpos = pos
    assert m1.enc_inpos == pos
    # TODO implement exception to configuration mode
    pos = get_random_pos()
    m1.enc_absenc = pos
    assert m1.enc_absenc == pos
    pos = get_random_pos()
    m1.enc_motor = pos
    assert m1.enc_motor == pos
    pos = get_random_pos()
    m1.enc_sync = pos
    assert m1.enc_sync == pos

    m1.velocity = 200
    assert m1.velocity == 200
    assert m1.velocity_current == 200
    assert m1.velocity_default == 50
    assert m1.velocity_max == 3000
    assert m1.velocity_min == 2

    with pytest.raises(AttributeError):
        m1.velocity_default = 100
    with pytest.raises(AttributeError):
        m1.velocity_min = 100
    with pytest.raises(AttributeError):
        m1.velocity_max = 100

    m1.acctime = 0.1
    assert m1.acctime == 0.1
    assert m1.acctime_default == 0.01
    assert m1.acctime_steps == 30

    assert m1.pcloop is True
    m1.pcloop = False
    assert m1.pcloop is False

    assert m1.indexer == 'INTERNAL'

    m1.infoa = ['LOW']
    assert set(m1.infoa) == {'LOW', 'NORMAL'}
    m1.infob = ['HIGH', 'NORMAL']
    assert set(m1.infob) == {'HIGH', 'NORMAL'}
    m1.infoc = ['LOW']
    assert set(m1.infoc) == {'LOW', 'NORMAL'}
    m1.outpaux = ['HIGH', 'NORMAL']
    assert set(m1.outpaux) == {'HIGH', 'NORMAL'}
    m1.outpos = ['MOTOR']
    assert set(m1.outpos) == {'MOTOR', 'NORMAL'}
    m1.syncpos = ['AXIS']
    assert set(m1.syncpos) == {'AXIS', 'NORMAL'}
    m1.syncaux = ['ENABLED', 'INVERTED']
    assert set(m1.syncaux) == {'ENABLED', 'INVERTED'}


def ice_auto_axes(f):
    """A helper which provides parametrized auto_axes version of icepap"""
    @pytest.mark.parametrize('auto_axes', [True, False],
                             ids=['smart', 'expert'])
    def wrapper(auto_axes):
        with mock_socket():
            pap = IcePAPController('icepap1', auto_axes=auto_axes)
            return f(pap)
    return wrapper


@pytest.mark.parametrize('auto_axes', [False, True],
                         ids=['expert', 'smart'])
def test_create_eth_icepap(auto_axes):
    with mock_socket():
        with pytest.raises(OSError):
            IcePAPController('weirdhost')
        with pytest.raises(OSError):
            IcePAPController('icepap1', 5001)
        ice = IcePAPController('icepap1', 5000)
        assert ice is not None


@ice_auto_axes
def test_connection(pap):
    assert pap.connected

    pap.disconnect()
    assert not pap.connected


@ice_auto_axes
def test_system(pap):
    assert pap.mode == 'OPER'
    m1 = pap[1]
    confirm_m1(m1)
    m1.pos = 55
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

    assert pap.get_states([1])[0].status_register == 0x00205013
    assert [s.status_register for s in pap.get_states([1, 5])] == \
           [0x00205013, 0x00205013]

    assert pap.get_power(1) == [True]
    assert pap.get_power([1]) == [True]
    assert pap.get_power([1, 151]) == [True, False]
    assert pap.get_power([151, 1]) == [False, True]

    with pytest.raises(ValueError):
        pap.get_pos('th')

    pap.add_alias('th', 1)

    assert pap.get_pos('th') == [55]


@ice_auto_axes
def test_racks(pap):
    assert pap.get_rid(0) == ['0008.0153.F797']
    assert pap.get_rid([0]) == ['0008.0153.F797']

    assert pap.get_rid([0, 15]) == ['0008.0153.F797', '0008.020B.1028']
    assert pap.get_rid([15, 0]) == ['0008.020B.1028', '0008.0153.F797']

    assert pap.get_rtemp(0) == [30.1]
    assert pap.get_rtemp([0]) == [30.1]

    assert pap.get_rtemp([0, 15]) == [30.1, 29.5]
    assert pap.get_rtemp([15, 0]) == [29.5, 30.1]


@ice_auto_axes
def test_axis_not_plugged(pap):
    with pytest.raises(ValueError):
        pap[200]

    # axis 2 is not installed but is valid
    m2 = pap[2]
    with pytest.raises(RuntimeError):
        m2.pos


def test_smart_axis(smart_pap):
    assert 1 in smart_pap
    assert 'th' not in smart_pap
    assert len(smart_pap.axes) == 3
    assert set(smart_pap.axes) == {1, 5, 151}

    drivers = smart_pap.drivers

    assert len(drivers) == 3

    with pytest.raises(ValueError):
        smart_pap[200]

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
    assert m1.status == 0x00205013
    assert m1.power is True
    confirm_m1(m1)
    m1.pos = 55
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
    assert m1.status == 0x00205013
    assert m1.power is True
    confirm_m1(m1)
    m1.pos = 55

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

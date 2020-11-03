import pytest

from icepap.group import Group, group


def test_group(smart_pap):
    m1, m5 = smart_pap[1, 5]
    grp = Group(smart_pap[1, 5])

    assert grp.controller == m1._ctrl
    assert grp.motors == [m1, m5]
    assert grp.names == ['th', 'tth']

    assert grp.get_pos() == [55, -3]
    assert grp.get_fpos() == [55, -3]

    expected_states = [m1.state.status_register, m5.state.status_register]
    assert [s.status_register for s in grp.get_states()] == expected_states

    assert grp.is_moving() is False

    grp = Group(smart_pap[1])
    assert grp.motors == [m1]

    grp = Group(smart_pap[1, 151])
    assert grp.get_power() == [True, False]
    assert grp.get_acctime() == [0.1, 0.25]
    assert grp.get_velocity() == [100, 1002]


def test_group_creation_helper(smart_pap):
    m1, m5 = smart_pap[1, 5]
    grp1 = group(*smart_pap[1, 5])
    assert grp1.motors == [m1, m5]
    assert grp1.names == ['th', 'tth']
    assert group(grp1) is grp1

    grp2 = group(smart_pap[1, 5])
    assert grp1.motors == grp2.motors

    m151, m152, m153 = smart_pap[151, 152, 153]
    grp3 = group(smart_pap[151, 152])
    grp4 = group(grp1, m153, grp3)
    assert grp4.motors == [m1, m5, m153, m151, m152]

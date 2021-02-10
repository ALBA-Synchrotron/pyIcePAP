import os
import time
import signal
import logging
import contextlib

import icepap.group


@contextlib.contextmanager
def ensure_power(obj, on=True):
    """
    Power context manager. Entering context ensures the motor(s) have power
    (or an exception is thrown). Leaving the context leaves motor(s) has we
    found them. The context manager object is an icepap.Group.

    :param obj: a Group, IcePAPAxis or a sequence of IcePAPAxis
    :param on: if True, ensures power on all motors and when leaving the
               context restores power off on the motors  that were powered
               of before. If False the reverse behavior is applied

    Example::

        from icepap import IcePAPController, ensure_power
        ipap = IcePAPController("ipap.acme.com")
        m1, m2 = ipap[1], ipap[2]
        m1.power = False
        m2.power = True
        assert (m1.power, m2.power) == (False, True)
        with ensure_power((m1, m2)) as group:
            assert (m1.power, m2.power) == (True, True)
            group.start_move((1000, 2000))
            group.wait_move()
        assert (m1.power, m2.power) == (False, True)
    """
    g = icepap.group.group(obj)
    ctrl = g.controller
    powers = g.get_power()
    to_power = [addr for addr, power in zip(g.axes, powers) if power != on]
    if to_power:
        ctrl.set_power(to_power, on)
    try:
        yield g
    finally:
        if to_power:
            ctrl.set_power(to_power, not on)


def is_moving(states):
    return any(state.is_moving() for state in states)


def calc_deltas(p1, p2):
    return [abs(a - b) for a, b in zip(p1, p2)]


def gen_move(group, target):
    with ensure_power(group):
        group.start_move(target)
        for event in gen_motion(group):
            yield event


def gen_rmove(group, target):
    with ensure_power(group):
        group.start_rmove(target)
        for event in gen_motion(group):
            yield event


def gen_motion(group):
    while True:
        states, positions = group.get_states(), group.get_pos()
        yield states, positions
        if not is_moving(states):
            break


def gen_rate_limiter(generator, period=0.1):
    last_update = 0
    for event in generator:
        nap = period - (time.monotonic() - last_update)
        if nap > 0:
            time.sleep(nap)
        yield event
        last_update = time.monotonic()


def interrupt_myself():
    os.kill(os.getpid(), signal.SIGINT)

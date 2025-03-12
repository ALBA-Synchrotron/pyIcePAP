# -----------------------------------------------------------------------------
# This file is part of icepap (https://github.com/ALBA-Synchrotron/pyIcePAP)
#
# Copyright 2008-2017 CELLS / ALBA Synchrotron, Bellaterra, Spain
#
# Distributed under the terms of the GNU General Public License,
# either version 3 of the License, or (at your option) any later version.
# See LICENSE.txt for more info.
#
# You should have received a copy of the GNU General Public License
# along with icepap. If not, see <http://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------
import time
import collections.abc
import contextlib

from .axis import IcePAPAxis
from .utils import State, is_moving, get_ctrl_item, get_item


class Group:

    def __init__(self, motors):
        if isinstance(motors, IcePAPAxis):
            motors = [motors]
        ctrls = set(motor._ctrl for motor in motors)
        assert len(ctrls) == 1, 'motors must be from same controller'
        self._controller = ctrls.pop()
        self._motors = motors
        self._names = None

    @property
    def controller(self):
        return self._controller

    @property
    def motors(self):
        return self._motors

    @property
    def names(self):
        if self._names is None:
            self._names = self.get_names()
        return self._names

    @property
    def axes(self):
        return [motor.axis for motor in self.motors]

    def get_names(self):
        return get_item(self.motors, "name")

    def get_acctime(self):
        return get_ctrl_item(self.controller.get_acctime, self.axes)

    def get_velocity(self):
        return get_ctrl_item(self.controller.get_velocity, self.axes)

    def get_pos(self):
        return get_ctrl_item(self.controller.get_pos, self.axes)

    def get_fpos(self):
        return get_ctrl_item(self.controller.get_fpos, self.axes)

    def get_states(self):
        return get_ctrl_item(self.controller.get_states, self.axes, State(0))

    def is_moving(self):
        return is_moving(self.get_states())

    def get_power(self):
        return get_ctrl_item(self.controller.get_power, self.axes)

    def start_stop(self):
        self._controller.stop(self.axes)

    def start_move(self, positions, **kwargs):
        args = [[mot.addr, pos] for mot, pos in zip(self._motors, positions)]
        self._controller.move(args, **kwargs)

    def start_rmove(self, positions, **kwargs):
        args = [[mot.addr, pos] for mot, pos in zip(self._motors, positions)]
        self._controller.rmove(args, **kwargs)

    def wait_stopped(self, timeout=None, interval=10e-3):
        """Helper loop to wait for group to finish moving"""

        start = time.time()
        while self.is_moving():
            time.sleep(interval)
            if timeout:
                elapsed = time.time() - start
                if elapsed > timeout:
                    return False
        return True


def group(*objs):
    if len(objs) == 1 and isinstance(objs[0], Group):
        return objs[0]
    motors = []
    for obj in objs:
        if isinstance(obj, IcePAPAxis):
            motors.append(obj)
        elif isinstance(obj, collections.abc.Sequence):
            motors.extend(group(*obj).motors)
        else:
            motors.extend(obj.motors)
    return Group(motors)


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
    g = group(obj)
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
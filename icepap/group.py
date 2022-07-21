import time
import collections.abc

from .axis import IcePAPAxis
from .utils import State


def get_ctrl_item(f, axes, default=None):
    try:
        return f(axes)
    except Exception:
        pass
    values = []
    for axis in axes:
        try:
            value = f(axis)[0]
        except RuntimeError:
            value = default
        values.append(value)
    return values


def get_item(motors, name, default=None):
    values = []
    for motor in motors:
        try:
            value = getattr(motor, name)
        except RuntimeError:
            value = default
        values.append(value)
    return values


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
        return any(state.is_moving() for state in self.get_states())

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

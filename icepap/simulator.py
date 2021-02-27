"""
.. code-block:: yaml

    devices:
    - class: IcePAP
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

import re
import enum
import time
import random
import inspect
import logging
import weakref
import functools
import collections

from motorlib import Motion, Jog
from sinstruments.simulator import BaseDevice


MAX_AXIS = 128


def iter_axis(start=1, stop=MAX_AXIS + 1, step=1):
    start, stop = max(start, 1), min(stop, MAX_AXIS + 1)
    for i in range(start, stop, step):
        if i % 10 > 8:
            continue
        yield i


VALID_AXES = list(iter_axis())

SYS_VER_INFO = """$
SYSTEM       :  3.17 : Tue Feb 16 10:57:37 2016
   CONTROLLER:  3.17
   DRIVER    :  3.17
$"""

DRIVER_VER_INFO = """$
SYSTEM       :  3.17 : Tue Feb 16 10:57:37 2016
   CONTROLLER:  3.17
   DRIVER    :  3.17
      DSP    :  3.67 : Mon Dec 14 13:22:03 2015
      FPGA   :  7.01 : Sat Mar  7 20:35:00 2015
      PCB    :  1.00
      IO     :  1.00
$"""

CTRL_VER_INFO = """$
SYSTEM       :  3.17 : Tue Feb 16 10:57:37 2016
   CONTROLLER:  3.17
      DSP    :  3.67 : Mon Dec 14 13:22:03 2015
      FPGA   :  1.00 : Tue Jan 21 19:33:00 2014
      PCB    :  1.00
   DRIVER    :  3.17
$"""

MASTER_VER_INFO = """$
SYSTEM       :  3.17 : Tue Feb 16 10:57:37 2016
   CONTROLLER:  3.17
      DSP    :  3.67 : Mon Dec 14 13:22:03 2015
      FPGA   :  1.00 : Tue Jan 21 19:33:00 2014
      PCB    :  1.00
      MCPU0  :  1.19
      MCPU1  :  1.19
      MCPU2  :  1.125
   DRIVER    :  3.17
$"""

CommandNotRecognized = "Command not recognised"
CannotBroadCastQuery = "Cannot broadcast a query"
CannotAcknowledgeBroadcast = "Cannot acknowledge a broadcast"
WrongParameters = "Wrong parameter(s)"
WrongNumberParameters = "Wrong number of parameter(s)"
TooManyParameters = "Too many parameters"
InvalidControllerBoardCommand = "Command or option not valid in controller boards"
BadBoardAddress = "Bad board address"
BoardNotPresent = "Board is not present in the system"


class IcePAPError(Exception):

    def __str__(self):
        return self.args[0]


def _result(cmd_result, result):
    if isinstance(result, IcePAPError):
        result = "ERROR {}".format(result)
    return "{} {}".format(cmd_result, result)


def _optional_args(args, options, default):
    if args and args[0].upper() in options:
        return args[0].upper(), args[1:]
    return default, args


AXIS_DEFAULTS = {
    "pos": 0,
    "velocity": 1,
    "acctime": 0.25,
    "status": 0x00A03203
}


class Axis(object):
    """IcePAP emulated axis"""

    def __init__(self, icepap, address=None, **opts):
        self.icepap = icepap
        self.motion = None
        self.address = address
        if address not in VALID_AXES:
            raise ValueError("{0} is not a valid address".format(address))
        self._log = logging.getLogger("{0}.{1}".format(icepap._log.name, address))
        opts = dict(AXIS_DEFAULTS, **opts)
        for k, v in opts.items():
            setattr(self, "_" + k, v)
        self._name = opts.get("name", "")

    def update(self, instant=None):
        if instant is None:
            instant = time.monotonic()
        if self.motion:
            self._pos = int(self.motion.position(instant))
            if self.motion.finished():
                self.motion = None
        if self.motion:
            self._status |= 0x400
        else:
            self._status &= 0xFFFFFBFF

    def name(self, value=None):
        if value is None:
            return self._name
        self._name = value

    def power(self, value=None):
        if value is None:
            return "ON" if self._status & (1 << 23) else "OFF"
        if value:
            self._status |= 1 << 23
        else:
            self._status &= 0xFFFFFFFF & ~(1 << 23)

    def position(self, selector='AXIS', value=None):
        self.update()
        if value is None:
            return self._pos
        else:
            self._pos = int(value)

    def status(self):
        self.update()
        return self._status

    def acctime(self, selector="NOMINAL", value=None):
        if value is None:
            return self._acctime
        self._acctime = float(value)

    def velocity(self, selector="NOMINAL", value=None):
        if value is None:
            if selector == "NOMINAL":
                return self._velocity
            elif selector == "CURRENT":
                self.update()
                if self.motion is None:
                    return 0
                return self.motion.velocity()
        self._velocity = float(value)

    def start_move(self, pf, instant=None, group=()):
        acceleration = self._velocity / self._acctime
        self.motion = Motion(
            self._pos, pf, self._velocity, acceleration, [float('-inf'), float('+inf')], ti=instant
        )
        self.motion.group = group

    def jog(self, velocity=None, instant=None, group=()):
        if velocity is None:
            self.update(instant)
            return self.motion.velocity(instant) if self.motion else 0
        if instant is None:
            instant = time.monotonic()
        self.update(instant)
        vi = self.motion.velocity(instant) if self.motion else 0
        self._log.info('jog from %s to %s', vi, velocity)
        accel = abs(self._velocity) / self._acctime
        try:
            self.motion = Jog(
                self._pos, velocity, accel, [float('-inf'), float('+inf')], vi, instant
            )
        except ValueError as error:
            raise IcePAPError(*error.args)
        self.motion.group = group

    def stop(self):
        self.update()
        if self.motion:
            for axis in self.motion.group:
                axis._stop()

    def _stop(self):
        self.update()
        if self.motion:
            self.motion.stop()


DEFAULTS = {
    "mode": "OPER",
    "ver": "3.17",
    "wtemp": "45"
}


class IcePAP(BaseDevice):
    """Emulated IcePAP"""

    newline = b"\r"

    _ACK = "(?P<ack>#)?"
    _ADDR = "((?P<addr>\d+)?(?P<broadcast>\:))?"
    _QUERY = "(?P<is_query>\\?)?"
    _INSTR = "(?P<instr>\\w+)"
    _CMD = re.compile(
        "{ack}\s*{addr}\s*{query}{instr}\s*".format(
            ack=_ACK, addr=_ADDR, query=_QUERY, instr=_INSTR
        )
    )

    def __init__(self, name, axes=None, **opts):
        super(IcePAP, self).__init__(name, **opts)
        axes_dict = {}
        for axis in axes or [dict(address=addr) for addr in iter_axis()]:
            axes_dict[axis["address"]] = Axis(self, **axis)
        self._axes = axes_dict
        opts = dict(DEFAULTS, **opts)
        for k, v in opts.items():
            setattr(self, "_" + k, v)

    def _get_racks(self):
        racks = collections.defaultdict(dict)
        for addr, axis in self._axes.items():
            racks[addr // 10][addr] = axis
        return racks

    @staticmethod
    def _cmd_result(cmd, cmd_match):
        """retrieve the command error message prefix from the command line"""
        if cmd_match is None:
            return cmd.replace("#", "").strip().split(" ", 1)[0]
        groups = cmd_match.groupdict()
        # replace None values with ''
        groups_str = dict([(k, ("" if v is None else v)) for k, v in groups.items()])
        groups_str["instr"] = groups_str["instr"].upper()
        return "{addr}{broadcast}{is_query}{instr}".format(**groups_str)

    def _get_axis(self, addr, system=False):
        if addr is None:
            raise IcePAPError(WrongNumberParameters)
        try:
            addr = int(addr)
        except ValueError:
            raise IcePAPError(WrongParameters)
        if addr is 0:
            raise IcePAPError(InvalidControllerBoardCommand)
        if addr > 256:
            raise IcePAPError(WrongParameters)
        if addr not in VALID_AXES:
            err = BadBoardAddress
            if not system:
                err = "ERROR Axis {}: {}".format(addr, err)
            raise ValueError(err)
        if addr not in self._axes:
            err = BoardNotPresent
            if not system:
                err = "ERROR Axis {}: {}".format(addr, err)
            raise IcePAPError(err)
        return self._axes[addr]

    def handle_message(self, line):
        self._log.debug("processing line %r", line)
        line = line.strip()
        responses = []
        for cmd in line.split(b";"):
            cmd = cmd.strip()
            response = self.handle_command(cmd)
            if response is not None:
                responses.append(response.encode('ascii') + b"\n")
        if responses:
            result = b"".join(responses)
            self._log.debug("answering with %r", result)
            return result

    def handle_command(self, cmd):
        self._log.debug("processing command %r", cmd)
        if not cmd:
            return
        cmd = cmd.decode()
        cmd_match = self._CMD.match(cmd)
        cmd_result = IcePAP._cmd_result(cmd, cmd_match)
        try:
            result = self._handle_command(cmd, cmd_match)
        except Exception as error:
            groups = cmd_match.groupdict()
            if groups["ack"] or groups["is_query"]:
                return _result(cmd_result, error)
        if result is not None:
            return _result(cmd_result, result)

    def _handle_command(self, cmd, cmd_match):
        if cmd_match is None:
            self._log.info("unable to parse command")
            raise IcePAPError(CommandNotRecognized)
        groups = cmd_match.groupdict()
        ack, addr = groups["ack"], groups["addr"]
        broadcast, is_query = groups["broadcast"], groups["is_query"]
        instr = groups["instr"].lower()
        if addr is not None:
            try:
                addr = int(addr)
            except ValueError:
                return
        if addr and not groups["broadcast"]:
            return
        broadcast = broadcast and addr is None
        if is_query and broadcast:
            raise IcePAPError(CannotBroadCastQuery)
        if ack and broadcast:
            raise IcePAPError(CannotAcknowledgeBroadcast)
        args = [arg.strip() for arg in cmd[cmd_match.end() :].split()]

        if instr == "name":
            instr = "handle_name"
        func = getattr(self, instr, None)
        if func is None:
            raise IcePAPError(CommandNotRecognized)
        else:
            result = func(
                is_query=is_query,
                broadcast=broadcast,
                ack=ack,
                args=args,
                addr=addr
            )
        if is_query or ack:
            return result

    def handle_name(self, is_query, broadcast, ack, args, addr):
        axis = self._get_axis(addr)
        if is_query:
            return axis.name()
        axis.name(value=args[0])
        if ack:
            return "OK"

    def addr(self, is_query, broadcast, ack, args, addr):
        if addr is None:
            raise IcePAPError(CommandNotRecognized)
        axis = self._get_axis(addr)
        return addr

    def fpos(self, is_query, broadcast, ack, args, addr):
        if addr is not None:
            raise IcePAPError(CommandNotRecognized)
        opts = {'AXIS', 'MEASURE'}
        selector, args = _optional_args(args, opts, 'AXIS')
        axes = [self._get_axis(axis) for axis in args]
        return " ".join(str(axis.position(selector=selector)) for axis in axes)

    def pos(self, is_query, broadcast, ack, args, addr):
        opts = {'AXIS', 'MEASURE', 'SHFTENC', 'TGTENC', 'CTRLENC', 'ENCIN', 'INPOS', 'ABSENC', 'MOTOR', 'SYNC'}
        selector, args = _optional_args(args, opts, 'AXIS')
        if addr is not None:
            args.insert(0, addr)
        if is_query:
            axes = [self._get_axis(axis) for axis in args]
            return " ".join(str(axis.position(selector=selector)) for axis in axes)
        else:
            axes = [self._get_axis(axis) for axis in args[::2]]
            positions = [int(arg) for arg in args[1::2]]
            for axis, position in zip(axes, positions):
                axis.position(selector=selector, value=position)
            if ack:
                return "OK"

    def fstatus(self, is_query, broadcast, ack, args, addr):
        if addr is not None:
            raise IcePAPError(CommandNotRecognized)
        axes = [self._get_axis(axis) for axis in args]
        return " ".join("0x{:X}".format(axis.status()) for axis in axes)

    def status(self, is_query, broadcast, ack, args, addr):
        if addr is not None:
            args = [addr]
        axes = [self._get_axis(axis) for axis in args]
        return " ".join("0x{:X}".format(axis.status()) for axis in axes)

    def power(self, is_query, broadcast, ack, args, addr):
        if is_query:
            if addr is not None:
                args.insert(0, addr)
            axes = [self._get_axis(axis) for axis in args]
            return " ".join(str(axis.power()) for axis in axes)
        else:
            on_off =args[0].upper() == 'ON'
            args = args[1:]
            if addr is not None:
                args.insert(0, addr)
            axes = [self._get_axis(axis) for axis in args]
            for axis in axes:
                axis.power(value=on_off)
            if ack:
                return "OK"
    def acctime(self, is_query, broadcast, ack, args, addr):
        opts = {'NOMINAL', 'STEPS', 'DEFAULT'}
        selector, args = _optional_args(args, opts, 'NOMINAL')
        if addr is not None:
            args.insert(0, addr)
        if is_query:
            axes = [self._get_axis(axis) for axis in args]
            return " ".join(str(axis.acctime(selector=selector)) for axis in axes)
        else:
            axes = [self._get_axis(axis) for axis in args[::2]]
            acctimes = [float(arg) for arg in args[1::2]]
            for axis, acctime in zip(axes, acctimes):
                axis.acctime(selector=selector, value=acctime)
            if ack:
                return "OK"

    def velocity(self, is_query, broadcast, ack, args, addr):
        opts = {'NOMINAL', 'MIN', 'MAX', 'CURRENT', 'DEFAULT'}
        selector, args = _optional_args(args, opts, 'NOMINAL')
        if addr is not None:
            args.insert(0, addr)
        if is_query:
            axes = [self._get_axis(axis) for axis in args]
            return " ".join(str(axis.velocity(selector=selector)) for axis in axes)
        else:
            axes = [self._get_axis(axis) for axis in args[::2]]
            velocities = [float(arg) for arg in args[1::2]]
            for axis, velocity in zip(axes, velocities):
                axis.velocity(value=velocity)
            if ack:
                return "OK"

    def mode(self, **kwargs):
        return self._mode

    def move(self, is_query, broadcast, ack, args, addr):
        group, strict = False, False
        if args[0].upper() == "GROUP":
            group = True
            args = args[1:]
        if args[0].upper() == "STRICT":
            strict = True
            args = args[1:]
        if addr is not None:
            args.insert(0, addr)
        axes = [self._get_axis(addr) for addr in args[::2]]
        positions = [int(pos) for pos in args[1::2]]
        start_time = time.monotonic()
        for axis, pos in zip(axes, positions):
            axis.start_move(pos, instant=start_time, group=axes if group else (axis,))
        if ack:
            return "OK"

    def stop(self, is_query, broadcast, ack, args, addr):
        if addr is not None:
            args.insert(0, addr)
        axes = [self._get_axis(addr) for addr in args]
        for axis in axes:
            axis.stop()
        if ack:
            return "OK"

    def jog(self, is_query, broadcast, ack, args, addr):
        if is_query:
            if addr is not None:
                args.insert(0, addr)
            axes = [self._get_axis(addr) for addr in args]
            return " ".join(str(axis.jog()) for axis in axes)
        group, strict = False, False
        if args[0].upper() == "GROUP":
            group = True
            args = args[1:]
        if args[0].upper() == "STRICT":
            strict = True
            args = args[1:]
        if addr is not None:
            args.insert(0, addr)
        axes = [self._get_axis(addr) for addr in args[::2]]
        velocities = [float(vel) for vel in args[1::2]]
        start_time = time.monotonic()
        for axis, vel in zip(axes, velocities):
            axis.jog(vel, instant=start_time, group=axes if group else (axis,))
        if ack:
            return "OK"

    def ver(self, is_query, broadcast, ack, args, addr):
        opts = {'SYSTEM', 'CONTROLLER', 'DRIVER', 'DSP', 'FPGA', 'PCB', 'IO', 'INFO'}
        selector, args = _optional_args(args, opts, 'SYSTEM')
        if selector == 'SYSTEM':
            return " {}".format(self._ver)
        elif selector == 'INFO':
            if addr is None:
                return SYS_VER_INFO
            addr = int(addr)
            if addr == 0:
                return MASTER_VER_INFO
            if addr in VALID_AXES:
                return DRIVER_VER_INFO
            return CTRL_VER_INFO

    def sysstat(self, is_query, broadcast, ack, args, addr):
        racks = self._get_racks()
        if not args:
            result = 0
            for rack in racks:
                result |= 1 << rack
            return "0x{:04X}".format(result)
        result = 0
        rack = int(args[0])
        if rack in racks:
            for axis in racks[rack]:
                axis -= rack * 10 + 1
                result |= 1 << axis
        return "0x{0:02X} 0x{0:02X}".format(result)

    def rid(self, is_query, broadcast, ack, args, addr):
        if not args:
            args = [0]
        return "0008.01C4.E8A{}".format(args[0])

    def rtemp(self, is_query, broadcast, ack, args, addr):
        if not args:
            args = [0]
        return " ".join(str(random.randint(30, 50)) for _ in args)

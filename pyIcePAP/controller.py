# ------------------------------------------------------------------------------
# This file is part of pyIcePAP (https://github.com/ALBA-Synchrotron/smaract)
#
# Copyright 2008-2017 CELLS / ALBA Synchrotron, Bellaterra, Spain
#
# Distributed under the terms of the GNU General Public License,
# either version 3 of the License, or (at your option) any later version.
# See LICENSE.txt for more info.
# ------------------------------------------------------------------------------

# General additions
# TODO: add logging
# TODO: export non official commands as advance commands in new API

# Changes to be supported from the old API
# TODO: export getTime
# TODO: export getSysStatus
# TODO: export getRackStatus
# TODO: export setDefaultConfig
# TODO: export getCurrent
# TODO: export readParameter
# TODO: export writeParameter
# TODO: export isExpertFlagSet
# TODO: export setExpertFlag
# TODO: export sendFirmware
# TODO: export getProgressStatus
# TODO: export getRacksAlive
# TODO: export getDriversAlive
# TODO: export getDecodedStatus
# TODO: export decodeStatus
# TODO: export serr
# TODO: export memory


__all__ = ['EthIcePAPController']

from future import *
from .communication import IcePAPCommunication, CommType
from .axis import IcePAPAxis


class IcePAPController(dict):
    """
    """

    def __init__(self, comm_type, *args):
        dict.__init__(self)
        self._comm = IcePAPCommunication(comm_type, *args)
        self._aliases = {}
        self._create_axes()

    def __getitem__(self, item):
        if isinstance(item, str):
            if item not in self._aliases:
                msg = 'There is not any motor with name {0}'.format(item)
                raise ValueError(msg)
            item = self._aliases[item]
        return dict.__getitem__(self, item)

    def _create_axes(self):
        # Take the list of racks present in the system
        # IcePAP user manual pag. 137
        racks_present = int(self._comm.send_cmd('?sysstat')[0], 16)
        rack_mask = 1
        duplicate_alias = []

        for i in range(16):
            if (racks_present & rack_mask << i) > 0:
                # Take the motors presents for a rack.
                cmd = '?sysstat {0}'.format(i)
                drivers_mask = self._comm.send_cmd(cmd)
                # TODO: Analyze if use the present or the alive mask
                # drvs_present = int(drivers_mask[0], 16)
                drvs_alives = int(drivers_mask[1], 16)
                drv_mask = 1
                for j in range(8):
                    if (drvs_alives & drv_mask << j) > 0:
                        axis_nr = i * 10 + j + 1
                        motor = IcePAPAxis(self, axis_nr)
                        self.__setitem__(axis_nr, motor)
                        motor_name = motor.name
                        if motor_name is None or motor_name == '':
                            continue
                        if motor_name in self._aliases:
                            self._aliases.pop(motor_name)
                            duplicate_alias.append(motor_name)
                            continue
                        if motor_name in duplicate_alias:
                            continue
                        self._aliases[motor_name.lower()] = axis_nr

    def _alias2axisstr(self, alias):
        """
        Method to get the axis motor number. The input can be: string or a
        number or a list with combination of strings and numbers. The result
        depends of the number of inputs.
        :param alias: str or int or [str, int, ...]
        :return: str
        """
        if isinstance(alias, int) or isinstance(alias, str):
            result = self.__getitem__(alias)._str_id
        elif isinstance(alias, list):
            result = []
            for i in alias:
                result.append(self._alias2axisstr(i))
            result = ' '.join(result)
        else:
            raise ValueError()
        return result

    def _axesvalues2str(self, axes_values):
        """
        Method to convert a list of tuples (axis, pos) to a string.
        :param axes_values: [[str/int,int]]
        :return: str
        """
        result = ''
        for axis, value in axes_values:
            result += '{0} {1} '.format(self._alias2axisstr(axis), value)
        return result

    @property
    def comm_type(self):
        """
        Get the communication type for this controller.

        :return: communication type
        """
        return self._comm.get_comm_type()

    @property
    def ver(self):
        """
        Get the version of the all driver modules: Driver, DSP, FPGA, PCB, IO,
        IcePAP user manual pag. 144

        :return: dict{module: (ver, date)}
        """
        ans = self.send_cmd('?VER INFO')
        result = {}
        for line in ans:
            v = line.split(':', 2)
            module = v[0].strip()
            value = float(v[1].strip())
            when = ''
            if len(v) > 2:
                when = v[2].strip()
            result[module] = (value, when)
        return result

    @property
    def mode(self):
        """
        Get the system mode
        IcePAP user manual pag. 91
        :return: str
        """
        return self.send_cmd('?MODE')[0]

    @mode.setter
    def mode(self, value):
        """
        Set the system mode
        :param value: str
        :return: None
        """
        cmd = 'MODE {0}'.format(value)
        self.send_cmd(cmd)

# -----------------------------------------------------------------------------
#                       Commands
# -----------------------------------------------------------------------------
    def send_cmd(self, cmd):
        """
        Communication function used to send any command to the IcePAP
        controller.
        :param cmd: string command following the Smaract ASCii Programming
        Interface.
        :return:
        """
        return self._comm.send_cmd(cmd)

    def move(self, axes_pos, group=True, strict=False):
        """
        Start absolute movement for axes motor. The method allows alias.
        :param axes_pos: [(str/int, int)]
        :param group: bool
        :param strict: bool
        :return: None
        """
        print axes_pos
        cmd = 'MOVE {0} {1} {2}'.format(['', 'GROUP'][group],
                                        ['', 'STRICT'][strict],
                                        self._axesvalues2str(axes_pos))
        self.send_cmd(cmd)

    def rmove(self, axes_pos, group=True, strict=False):
        """
        Start relative movement for axes motor. The method allows alias.
        :param axes_pos: [(str/int,int)]
        :param group: bool
        :param strict: bool
        :return: None
        """

        cmd = 'RMOVE {0} {1} {2}'.format(['', 'GROUP'][group],
                                         ['', 'STRICT'][strict],
                                         self._axesvalues2str(axes_pos))
        self.send_cmd(cmd)

    def movep(self, pos, axes, group=True, strict=False):
        """
        Start axes movement to parameter value
        :param pos: float
        :param axes: [str/int]
        :param group: bool
        :param strict: bool
        :return: None
        """

        cmd = 'MOVEP {0} {1} {2} {3}'.format(['', 'GROUP'][group],
                                             ['', 'STRICT'][strict],
                                             pos,
                                             self._alias2axisstr(axes))
        self.send_cmd(cmd)

    def pmove(self, pos, axes, group=False, strict=False):
        """
        Start parameter movement.
        :param pos: float
        :param axes: [str/int]
        :param group: bool
        :param strict: bool
        :return: None
        """
        cmd = 'PMOVE {0} {1} {2} {3}'.format(['', 'GROUP'][group],
                                             ['', 'STRICT'][strict],
                                             pos,
                                             self._alias2axisstr(axes))
        self.send_cmd(cmd)

    def stop(self, axes):
        """
        Stop multiple axis movement
        IcePAP user manual pag. 129
        :param axes: [str/int]
        :return: None
        """
        cmd = 'STOP {0}'.format(self._alias2axisstr(axes))
        self.send_cmd(cmd)

    def abort(self, axes):
        """
        Abort multiple axis movement
        IcePAP user manual pag. 129
        :param axes: [str/int]
        :return: None
        """
        cmd = 'ABORT {0}'.format(self._alias2axisstr(axes))
        self.send_cmd(cmd)

    def get_fpos(self, axes, register='AXIS'):
        """
        Fast read of multiple positions
        IcePAP user manual pag. 73
        :param axes: [str/int]
        :param register: str
        :return: [float]
        """
        cmd = '?FPOS {0} {1}'.format(register, self._alias2axisstr(axes))
        ans = self.send_cmd(cmd)
        return map(float, ans)

    def get_fstatus(self, axes):
        """
        Fast read of multiple status.
        IcePAP user manual. pag. 74
        :param axes: [str/int]
        :return: [int]
        """
        cmd = '?FSTATUS {0}'.format(self._alias2axisstr(axes))
        ans  = self.send_cmd(cmd)
        return [int(i, 16) for i in ans]

    def get_status(self, axes):
        """
        Read of multiple status.
        IcePAP user manual. pag. 128
        :param axes: [str/int]
        :return: [int]
        """
        cmd = '?STATUS {0}'.format(self._alias2axisstr(axes))
        ans  = self.send_cmd(cmd)
        return [int(i, 16) for i in ans]

    def reboot(self):
        """
        System reboot.
        IcePAP user manual pag. 115
        :return: None
        """
        self.send_cmd('REBOOT')

    def reset(self, rack_nr=None):
        """
        Reset system or rack.
        IcePAP user manual pag. 117
        :return: None
        """
        if rack_nr is None:
            rack_nr = ''
        cmd = 'RESET {0}'.format(rack_nr)
        self.send_cmd(cmd)

    def get_rid(self, rack_nrs):
        """
        Get the rack hardware identification string.
        IcePAP user manual pag. 118
        :param rack_nrs: [int]
        :return: [str]
        """

        racks_str = ' '.join(['{0:x}'.format(i) for i in rack_nrs])
        cmd = '?RID {0}'.format(racks_str)
        return self.send_cmd(cmd)

    def get_rtemp(self, rack_nrs):
        """
        Get the rack temperatures.
        IcePAP user manual pag. 123
        :param rack_nrs: [int]
        :return: [float]
        """

        racks_str = ' '.join(['{0:x}'.format(i) for i in rack_nrs])
        cmd = '?RTEMP {0}'.format(racks_str)
        return map(float, self.send_cmd(cmd))

    def set_power(self, axes, power_on=True):
        """
        Set axes power state
        :param axes: [str/int]
        :param power_on: bool
        :return: None
        """
        cmd = 'POWER {0} {1}'.format(['OFF', 'ON'][power_on],
                                     self._alias2axisstr(axes))
        self.send_cmd(cmd)

    def get_power(self, axes):
        """
        Get axes power state
        :param axes: [str/int]
        :return: [bool]
        """
        cmd = '?POWER {0}'.format(self._alias2axisstr(axes))
        ans = self.send_cmd(cmd)
        return [i.upper() == 'ON' for i in ans]

    def print_commands(self):
        """
        Get the allows commands ?HELP
        IcePAP user manual pag. 75
        :return: None
        """
        ans = self.send_cmd('?HELP')
        print('\n'.join(ans))

    def get_pos(self, axes, register='AXIS'):
        """
        Get multiple position
        :param axes: [str/int]
        :param register: str
        :return: [float]
        """
        cmd = '?POS {0} {1}'.format(register, self._alias2axisstr(axes))
        ans = self.send_cmd(cmd)
        return map(float, ans)

    def set_pos(self, axes_pos, register='AXIS'):
        """
        Set multiple positions
        :param axes_pos: [(str/int,int)]
        :param register: str
        :return: None
        """
        cmd = 'POS {0} {1}'.format(register, self._axesvalues2str(axes_pos))
        self.send_cmd(cmd)

    def get_enc(self, axes, register='AXIS'):
        """
        Get multiple encoder
        :param axes: [str/int]
        :param register: str
        :return: [float]
        """
        cmd = '?ENC {0} {1}'.format(register, self._alias2axisstr(axes))
        ans = self.send_cmd(cmd)
        return map(float, ans)

    def set_enc(self, axes_pos, register='AXIS'):
        """
        Set multiple encoder
        :param axes_pos: [(str/int,int)]
        :param register: str
        :return: None
        """
        cmd = 'ENC {0} {1}'.format(register, self._axesvalues2str(axes_pos))
        self.send_cmd(cmd)

    def get_homestat(self, axes):
        """
        Get home search status
        :param axes: [str/int]
        :return: [(str,int)] list of Status, Direction per motor
        """
        cmd = '?HOMESTAT {0}'.format(self._alias2axisstr(axes))
        ans = self.send_cmd(cmd)
        return [(ans[i-1], int(v)) for i, v in enumerate(ans) if i % 2 > 0]

    def get_velocity(self, axes, vtype='NOMINAL'):
        """
        Get multiple velocities
        IcePAP user manual pag. 141

        :param axes: [str/int]
        :return: [float]
        """
        cmd = '?VELOCITY {0} {1}'.format(vtype, self._alias2axisstr(axes))
        ans = self.send_cmd(cmd)
        return map(float, ans)

    def set_velocity(self, axes_vel):
        """
        Set multiple velocities.
        Icepap user manual pag. 141

        :param axes_vel: [(str/int, float)]
        :return: None
        """
        cmd = 'VELOCITY {0}'.format(self._axesvalues2str(axes_vel))
        self.send_cmd(cmd)

    def get_acctime(self, axes, atype='NOMINAL'):
        """
        Get multiple velocities
        IcePAP user manual pag. 141

        :param axes: [str/int]
        :return: [float]
        """
        cmd = '?ACCTIME {0} {1}'.format(atype, self._alias2axisstr(axes))
        ans = self.send_cmd(cmd)
        return map(float, ans)

    def set_acctime(self, axes_acc):
        """
        Set multiple velocities.
        Icepap user manual pag. 141

        :param axes_vel: [(str/int, float)]
        :return: None
        """
        cmd = 'ACCTIME {0}'.format(self._axesvalues2str(axes_acc))
        self.send_cmd(cmd)

    def esync(self, axes):
        """
        Synchronize internal position register for multiple axis
        :param axes: [str/int]
        :return: None
        """
        cmd = 'ESYNC {0}'.format(self._alias2axisstr(axes))
        self.send_cmd(cmd)

    def ctrlrst(self, axes):
        """
        Reset control position register for multiple axis
        :param axes: [str/int]
        :return: None
        """
        cmd = 'CTRLRST {0}'.format(self._alias2axisstr(axes))
        self.send_cmd(cmd)


class EthIcePAPController(IcePAPController):
    def __init__(self, host, port=5000):
        IcePAPController.__init__(self, CommType.Socket, host, port)


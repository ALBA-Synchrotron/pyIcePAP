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

# General additions
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
# TODO: export getRacksAlive
# TODO: export getDriversAlive
# TODO: export getDecodedStatus
# TODO: export decodeStatus
# TODO: export serr
# TODO: export memory


__all__ = ['IcePAPController']

import time
import logging
import array
import urllib.parse
import collections.abc
from .communication import IcePAPCommunication
from .axis import IcePAPAxis
from .utils import State
from .fwversion import SUPPORTED_VERSIONS, FirmwareVersion


class IcePAPController:
    """
    IcePAP motor controller class.
    """
    ALL_AXES_VALID = set([r * 10 + i for r in range(16) for i in range(1, 9)])

    def __init__(self, host, port=5000, timeout=3, auto_axes=False, **kwargs):
        log_name = '{0}.IcePAPController'.format(__name__)
        self.log = logging.getLogger(log_name)

        self._comm = IcePAPCommunication(host, port, timeout)

        self._aliases = {}
        self._axes = {}

        if auto_axes:
            for axis in self.find_axes(only_alive=True):
                self._axes[axis] = IcePAPAxis(self, axis)

    def __getitem__(self, item):
        if isinstance(item, str):
            item = self._get_axis_for_alias(item)
        elif isinstance(item, collections.abc.Sequence):
            return [self[i] for i in item]
        if item not in self._axes:
            if item not in self.ALL_AXES_VALID:
                raise ValueError('Bad axis value.')
            self._axes[item] = IcePAPAxis(self, item)
        return self._axes[item]

    def __iter__(self):
        return self._axes.__iter__()

    def __delitem__(self, key):
        self._axes.pop(key)
        aliases_to_remove = []
        for alias, axis in self._aliases.items():
            if key == axis:
                aliases_to_remove.append(alias)
        for alias in aliases_to_remove:
            self._aliases.pop(alias)

    def __repr__(self):
        return '{}({}:{})'.format(type(self).__name__,
                                  self._comm.host, self._comm.port)

    def __str__(self):
        msg = 'IcePAPController connected ' \
              'to {}:{}'.format(self._comm.host, self._comm.port)
        return msg

    def _get_axis_for_alias(self, alias):
        if alias not in self._aliases:
            msg = 'There is not any motor with name {0}'.format(alias)
            raise ValueError(msg)
        alias = self._aliases[alias]
        return alias

    def _alias2axisstr(self, alias):
        """
        Method to get the axis motor number. The input can be: string or a
        number or IcePAPAxis or a list with combination of strings and
        numbers. The result depends of the number of inputs.

        :param alias: IcePAPAxis or str or int or [str, int, IcePAPAxis, ...]

        :return: str
        """
        if isinstance(alias, int):
            result = str(alias)
        elif isinstance(alias, str):
            result = str(self._get_axis_for_alias(alias))
        elif isinstance(alias, IcePAPAxis):
            result = str(alias.axis)
        elif isinstance(alias, list):
            result = []
            for i in alias:
                result.append(self._alias2axisstr(i))
            result = ' '.join(result)
        else:
            raise ValueError()
        return result

    def _axesvalues2str(self, axes_values, cast_type=int):
        """
        Method to convert a list of tuples (axis, pos) to a string.

        :param axes_values: [[str/int, float/int]]

        :return: str
        """
        result = ''
        for axis, value in axes_values:
            result += '{0} {1} '.format(self._alias2axisstr(axis),
                                        cast_type(value))
        return result

    @classmethod
    def from_url(cls, url):
        if "://" not in url:
            url = "tcp://" + url
        addr = urllib.parse.urlparse(url)
        return cls(addr.hostname, addr.port or 5000)

# -----------------------------------------------------------------------------
#                       Properties
# -----------------------------------------------------------------------------
    @property
    def host(self):
        return self._comm.host

    @property
    def port(self):
        return self._comm.port

    @property
    def axes(self):
        """
        Get the axes numbers.

        :return: [int]
        """
        axes = list(self._axes.keys())
        axes.sort()
        return axes

    @property
    def drivers(self):
        """
        Get the drivers IcePAPAxis objects.

        :return: [IcePAPAxis]
        """
        return list(self._axes.values())

    @property
    def ver(self):
        """
        Get the version of the all driver modules: Driver, DSP, FPGA, PCB, IO
        (IcePAP user manual pag. 144).

        :return: dict{module: (ver, date)}
        """
        ans = self.send_cmd('0:?VER INFO')
        return FirmwareVersion(ans)

    @property
    def fver(self):
        """
        Get the only system version '?VER'
        (IcePAP user manual pag. 144).

        :return: float
        """
        ans = self.send_cmd('?VER')[0]
        return float(ans)

    @property
    def ver_saved(self):
        """
        Returns the firmware version stored in the master flash memory.

        :return: dict{}
        """
        ans = self.send_cmd('?VER SAVED')
        return FirmwareVersion(ans)

    @property
    def connected(self):
        return self._comm.is_connected()

    @property
    def mode(self):
        """
        Get the system mode (IcePAP user manual pag. 91).

        :return: str
        """
        return self.send_cmd('?MODE')[0]

    @mode.setter
    def mode(self, value):
        """
        Set the system mode.

        :param value: str
        """
        cmd = 'MODE {0}'.format(value)
        self.send_cmd(cmd)

    @property
    def multiline_answer(self):
        return self._comm.multiline_answer
# -----------------------------------------------------------------------------
#                       Commands
# -----------------------------------------------------------------------------

    def items(self):
        """
        Get the axes and drivers IcePAPAxis objects.

        :return: [(axis, IcePAPAxis),]
        """

        return list(self._axes.items())

    def find_axes(self, only_alive=False):

        # Take the list of racks present in the system
        # IcePAP user manual pag. 137
        racks_present = int(self._comm.send_cmd('?sysstat')[0], 16)
        rack_mask = 1
        axes = []
        for i in range(16):
            if (racks_present & rack_mask << i) > 0:
                # Take the motors presents for a rack.
                cmd = '?sysstat {0}'.format(i)
                drivers_mask = self._comm.send_cmd(cmd)
                # TODO: Analyze if use the present or the alive mask
                if only_alive:
                    # Drivers alive
                    drvs = int(drivers_mask[1], 16)
                else:
                    # Drivers present
                    drvs = int(drivers_mask[0], 16)
                drv_mask = 1
                for j in range(8):
                    if (drvs & drv_mask << j) > 0:
                        axis_nr = i * 10 + j + 1
                        axes.append(axis_nr)
        return axes

    def find_racks(self):
        racks_present = int(self._comm.send_cmd('?sysstat')[0], 16)
        racks_mask = 1
        racks = []
        for i in range(16):
            if (racks_present & racks_mask << i) > 0:
                racks.append(i)
        return racks

    def update_axes(self):
        """
        Method to check if the axes created are presents. In case of no,
        the method will remove the IcePAPAxis object and its aliases.

        Note: The axis can be present but not alive

        :return:
        """
        alive_axes = self.find_axes()
        axes_to_remove = []

        for axis in self._axes:
            if axis not in alive_axes:
                axes_to_remove.append(axis)

        for axis in axes_to_remove:
            self.__delitem__(axis)

    def add_alias(self, alias, axis):
        """
        Set a alias for an axis. The axis can have more than one alias.

        :param alias: str
        :param axis: int
        """
        if axis not in self._axes:
            self._axes[axis] = IcePAPAxis(self, axis)
        self._aliases[alias] = axis

    def add_aliases(self, aliases):
        """
        Set alias for mutiple axes.

        :param aliases: {str: int}
        """
        for alias, axis in aliases.items():
            self.add_alias(alias, axis)

    def get_aliases(self):
        """
        Get the aliases of the system. One axis can have move than one alias.

        :return: {int:[str]}
        """
        aliases = {}
        for key, value in self._aliases.items():
            if value in aliases:
                aliases[value].append(key)
            else:
                aliases[value] = [key]
        return aliases

# -----------------------------------------------------------------------------
#                       IcePAP Commands
# -----------------------------------------------------------------------------
    def send_cmd(self, cmd):
        """
        Communication function used to send any command to the IcePAP
        controller.

        :param cmd: string command following the Programming Interface.

        :return: None or list of string without the command and the CRLF.
        """
        return self._comm.send_cmd(cmd)

    def move(self, axes_pos, group=True, strict=False):
        """
        Start absolute movement for axes motor. The method allows aliases.

        :param axes_pos: [(str/int, int)]
        :param group: bool
        :param strict: bool
        """
        cmd = 'MOVE {0} {1} {2}'.format(['', 'GROUP'][group],
                                        ['', 'STRICT'][strict],
                                        self._axesvalues2str(axes_pos))
        self.send_cmd(cmd)

    def rmove(self, axes_pos, group=True, strict=False):
        """
        Start relative movement for axes motor. The method allows aliases.

        :param axes_pos: [(str/int,int)]
        :param group: bool
        :param strict: bool
        """

        cmd = 'RMOVE {0} {1} {2}'.format(['', 'GROUP'][group],
                                         ['', 'STRICT'][strict],
                                         self._axesvalues2str(axes_pos))
        self.send_cmd(cmd)

    def movep(self, pos, axes, group=True, strict=False):
        """
        Start axes movement to parameter value.

        :param pos: float
        :param axes: [str/int]
        :param group: bool
        :param strict: bool
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
        """
        cmd = 'PMOVE {0} {1} {2} {3}'.format(['', 'GROUP'][group],
                                             ['', 'STRICT'][strict],
                                             pos,
                                             self._alias2axisstr(axes))
        self.send_cmd(cmd)

    def stop(self, axes):
        """
        Stop multiple axis movement (IcePAP user manual pag. 129).

        :param axes: [str/int]
        """
        cmd = 'STOP {0}'.format(self._alias2axisstr(axes))
        self.send_cmd(cmd)

    def abort(self, axes):
        """
        Abort multiple axis movement (IcePAP user manual pag. 129).

        :param axes: [str/int]
        """
        cmd = 'ABORT {0}'.format(self._alias2axisstr(axes))
        self.send_cmd(cmd)

    def get_fpos(self, axes, register='AXIS'):
        """
        Fast read of multiple positions (IcePAP user manual pag. 73).

        :param axes: [str/int]
        :param register: str
        :return: [int]
        """
        cmd = '?FPOS {0} {1}'.format(register, self._alias2axisstr(axes))
        ans = self.send_cmd(cmd)
        return list(map(int, ans))

    def get_fstatus(self, axes):
        """
        Fast read of multiple status (IcePAP user manual pag. 74).

        :param axes: [str/int]
        :return: [int]
        """
        cmd = '?FSTATUS {0}'.format(self._alias2axisstr(axes))
        ans = self.send_cmd(cmd)
        return [int(i, 16) for i in ans]

    def get_states(self, axes):
        """
        Fast read of the multiples status

        :param axes: [str/int]
        :return: [State]
        """
        fstatus = self.get_fstatus(axes)
        return [State(i) for i in fstatus]

    def get_status(self, axes):
        """
        Read of multiple status (IcePAP user manual pag. 128).

        :param axes: [str/int]
        :return: [int]
        """
        cmd = '?STATUS {0}'.format(self._alias2axisstr(axes))
        ans = self.send_cmd(cmd)
        return [int(i, 16) for i in ans]

    # TODO: optionally compare against saved version.
    def check_version(self):
        """
        Compares the current version installed with the supported
        versions specified in the versions module.

        :return: system version number, -1 if not consistent.
        """
        sys_ver = str(self.ver['SYSTEM']['VER'][0])
        if sys_ver in list(SUPPORTED_VERSIONS.keys()):
            if self.ver.is_supported():
                return self.ver['SYSTEM']['VER'][0]
            else:
                print('Modules versions are not consistent.')
                return -1
        else:
            raise RuntimeError('Version %s not supported' %
                               self.ver['SYSTEM']['VER'][0])

    def reboot(self):
        """
        System reboot (IcePAP user manual pag. 115).
        """
        self.send_cmd('REBOOT')

    def reset(self, rack_nr=None):
        """
        Reset system or rack (IcePAP user manual pag. 117).
        """
        if rack_nr is None:
            rack_nr = ''
        cmd = 'RESET {0}'.format(rack_nr)
        self.send_cmd(cmd)

    def get_rid(self, rack_nrs):
        """
        Get the rack hardware identification string (IcePAP user manual pag.
        118).

        :param rack_nrs: int/[int]
        :return: [str]
        """
        if isinstance(rack_nrs, int):
            rack_nrs = [rack_nrs]
        racks_str = ' '.join(['{}'.format(i) for i in rack_nrs])
        cmd = '?RID {0}'.format(racks_str)
        return self.send_cmd(cmd)

    def get_rtemp(self, rack_nrs):
        """
        Get the rack temperatures (IcePAP user manual pag. 123).

        :param rack_nrs: int/[int]
        :return: [float]
        """
        if isinstance(rack_nrs, int):
            rack_nrs = [rack_nrs]
        racks_str = ' '.join(['{}'.format(i) for i in rack_nrs])
        cmd = '?RTEMP {0}'.format(racks_str)
        return list(map(float, self.send_cmd(cmd)))

    def set_power(self, axes, power_on=True):
        """
        Set axes power state.

        :param axes: [str/int]
        :param power_on: bool
        """
        cmd = 'POWER {0} {1}'.format(['OFF', 'ON'][power_on],
                                     self._alias2axisstr(axes))
        self.send_cmd(cmd)

    def get_power(self, axes):
        """
        Get axes power state.

        :param axes: [str/int]
        :return: [bool]
        """
        cmd = '?POWER {0}'.format(self._alias2axisstr(axes))
        ans = self.send_cmd(cmd)
        return [i.upper() == 'ON' for i in ans]

    def print_commands(self):
        """
        Get the allowed commands (IcePAP user manual pag. 75).
        """
        ans = self.send_cmd('?HELP')
        print('\n'.join(ans))

    def get_pos(self, axes, register='AXIS'):
        """
        Get multiple position.

        :param axes: [str/int]
        :param register: str
        :return: [float]
        """
        cmd = '?POS {0} {1}'.format(register, self._alias2axisstr(axes))
        ans = self.send_cmd(cmd)
        return list(map(int, ans))

    def set_pos(self, axes_pos, register='AXIS'):
        """
        Set multiple positions.

        :param axes_pos: [(str/int,int)]
        :param register: str
        """
        cmd = 'POS {0} {1}'.format(register, self._axesvalues2str(axes_pos))
        self.send_cmd(cmd)

    def get_enc(self, axes, register='AXIS'):
        """
        Get multiple encoder.

        :param axes: [str/int]
        :param register: str
        :return: [float]
        """
        cmd = '?ENC {0} {1}'.format(register, self._alias2axisstr(axes))
        ans = self.send_cmd(cmd)
        return list(map(int, ans))

    def set_enc(self, axes_pos, register='AXIS'):
        """
        Set multiple encoder.

        :param axes_pos: [(str/int,int)]
        :param register: str
        """
        cmd = 'ENC {0} {1}'.format(register, self._axesvalues2str(axes_pos))
        self.send_cmd(cmd)

    def get_homestat(self, axes):
        """
        Get home search status.

        :param axes: [str/int]
        :return: [(str,int)] list of Status, Direction per motor
        """
        cmd = '?HOMESTAT {0}'.format(self._alias2axisstr(axes))
        ans = self.send_cmd(cmd)
        return [(ans[i-1], int(v)) for i, v in enumerate(ans) if i % 2 > 0]

    def get_velocity(self, axes, vtype='NOMINAL'):
        """
        Get multiple velocities (IcePAP user manual pag. 141).

        :param axes: [str/int]
        :return: [float]
        """
        cmd = '?VELOCITY {0} {1}'.format(vtype, self._alias2axisstr(axes))
        ans = self.send_cmd(cmd)
        return list(map(float, ans))

    def set_velocity(self, axes_vel):
        """
        Set multiple velocities (Icepap user manual pag. 141).

        :param axes_vel: [(str/int, float)]
        """
        cmd = 'VELOCITY {0}'.format(self._axesvalues2str(axes_vel,
                                                         cast_type=float))
        self.send_cmd(cmd)

    def get_acctime(self, axes, atype='NOMINAL'):
        """
        Get multiple velocities (IcePAP user manual pag. 141).

        :param axes: [str/int]
        :return: [float]
        """
        cmd = '?ACCTIME {0} {1}'.format(atype, self._alias2axisstr(axes))
        ans = self.send_cmd(cmd)
        return list(map(float, ans))

    def set_acctime(self, axes_acc):
        """
        Set multiple velocities (Icepap user manual pag. 141).

        :param axes_acc: [(str/int, float)]
        """
        cmd = 'ACCTIME {0}'.format(self._axesvalues2str(axes_acc,
                                                        cast_type=float))
        self.send_cmd(cmd)

    def esync(self, axes):
        """
        Synchronize internal position register for multiple axis.

        :param axes: [str/int]
        """
        cmd = 'ESYNC {0}'.format(self._alias2axisstr(axes))
        self.send_cmd(cmd)

    def ctrlrst(self, axes):
        """
        Reset control position register for multiple axis.

        :param axes: [str/int]
        """
        cmd = 'CTRLRST {0}'.format(self._alias2axisstr(axes))
        self.send_cmd(cmd)

    def clear_pmux(self, dest=''):
        """
        Clear the multiplexer configuration. You can pass a destination with
        an optional signal or just the signals to remove (IcePAP user manual,
        page 107).

        :param dest: node to remove
        """
        cmd = 'PMUX REMOVE {0}'.format(dest)
        self.send_cmd(cmd)

    def add_pmux(self, source, dest='', pos=True, aux=True, hard=False):
        """
        Configures a position signal multiplexer configuration (IcePAP user
        manual, page 107).

        :param source: Source node
        :param dest: Target node
        :param pos: Connect the Position signals
        :param aux: Connect the Auxiliary signals
        :param hard: Enabling/Disabling hard flag connection.
        """
        cmd = 'PMUX {0} {1} {2} {3} {4}'.format(['', 'HARD'][hard],
                                                ['', 'POS'][pos],
                                                ['', 'AUX'][aux],
                                                source,
                                                dest)
        self.send_cmd(cmd)

    def get_pmux(self):
        """
        Returns a list of the current signals sources used as axis indexers
        (IcePAP user manual, page 107).

        :return: list of multiplexer configurations.
        """
        return self.send_cmd('?PMUX')

    def get_linked(self):
        """
        Returns the current list of groups of linked drivers. 
        Each group is returned in a separate line starting by the name 
        of the group and followed by the corresponding list of axes.

        (IcePAP user manual, page 80).

        :return: list of groups of linked drivers.
        """
        return self.send_cmd('?LINKED')

    def sprog(self, filename, component=None, force=False, saving=False,
              options=''):
        """
        Firmware programming command. This command assumes that the firmware
        code will be transferred as a binary data block (IcePAP user manual,
        page 112).
        :param filename: firmware filename
        :param component: { NONE | board adress | DRIVERS | CONTROLLERS| ALL }
        :param force: Force overwrite regardless of being idential versions.
        :param saving: Saves firmware into master board flash.
        :param options: extra options
        """
        force_str = ''
        if component:
            comp_str = str(component).upper()
        else:
            comp_str = 'NONE'
        if force:
            force_str = 'FORCE'
        if not saving:
            save_str = 'NOSAVE'
        else:
            save_str = 'SAVE'
        cmd = '*PROG {} {} {} {}'.format(comp_str, force_str, save_str,
                                         options)
        self.send_cmd(cmd)

        with open(filename, 'rb') as f:
            data = f.read()
        data = array.array('H', data)
        self._comm.send_binary(ushort_data=data)

    def prog(self, component, force=False):
        """
        Firmware programming command. This command uses the firmware code
        previously stored in the flash memory of the system master board
        (IcePAP user manual, page 112).

        :param component: { board adress | DRIVERS | CONTROLLERS| ALL }
        :param force: Force overwrite regardless of being idential versions.
        """
        force_str = ''
        if force:
            force_str = 'FORCE'
        prog_str = 'PROG'

        cmd = '{} {} {}'.format(prog_str, str(component).upper(), force_str)
        self.send_cmd(cmd)
        time.sleep(5)

    def get_prog_status(self):
        """
        Request the state of the firmware programing operations (IcePAP user
        manual, page 112).

        :return: { OFF | ACTIVE <progress> | DONE | ERROR }
        """
        try:
            ans = self.send_cmd('?PROG')
        except RuntimeError:
            ans = self.send_cmd('?_PROG')
        return ans

    def disconnect(self):
        """
        Method to close the communication with the IcePAP
        :return:
        """

        self._comm.disconnect()

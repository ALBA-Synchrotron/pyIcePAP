# ------------------------------------------------------------------------------
# This file is part of pyIcePAP (https://github.com/ALBA-Synchrotron/smaract)
#
# Copyright 2008-2017 CELLS / ALBA Synchrotron, Bellaterra, Spain
#
# Distributed under the terms of the GNU General Public License,
# either version 3 of the License, or (at your option) any later version.
# See LICENSE.txt for more info.
# ------------------------------------------------------------------------------

__all__ = ['IcePAPController']

from .communication import IcePAPCommunication
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
                        self._aliases[motor_name.lower()] = axis_nr

    def _alias2axis(self, alias):
        """
        Method to get the axis motor number. The input can be: string or a
        number or a list with combination of strings and numbers. The result
        depends of the number of inputs.
        :param alias: str or int or [str, int, ...]
        :return: int or [int]
        """

        if isinstance(alias, int):
            result = alias
        elif isinstance(alias, str):
            alias = alias.lower()
            if alias in self._aliases:
                result = self._aliases[alias]
        elif isinstance(alias, list):
            result = []
            for i in alias:
                result.append(self._alias2axis(i))
        else:
            raise ValueError()
        return result

    def _axespos2str(self, axes_pos):
        """
        Method to convert a list of tuples (axis, pos) to a string.
        :param axes_pos: [[str/int,int]]
        :return: str
        """
        result = ''
        for axis, pos in axes_pos:
            result += '{0} {1} '.format(self._alias2axis(axis), pos)
        return result

    @property
    def comm_type(self):
        """
        Get the communication type for this controller.

        :return: communication type
        """
        return self._comm.get_comm_type()

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
        :param axes_pos: [[str/int,int]]
        :param group: bool
        :param strict: bool
        :return: None
        """

        cmd = 'MOVE {0} {1} {2}'.format(['', 'GROUP'][group],
                                        ['', 'STRICT'][strict],
                                        self._axespos2str(axes_pos))
        self.send_cmd(cmd)

    def rmove(self, axes_pos, group=True, strict=False):
        """
        Start relative movement for axes motor. The method allows alias.
        :param axes_pos: [[str/int,int]]
        :param group: bool
        :param strict: bool
        :return: None
        """

        cmd = 'RMOVE {0} {1} {2}'.format(['', 'GROUP'][group],
                                         ['', 'STRICT'][strict],
                                         self._axespos2str(axes_pos))
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
        axes = self._alias2axis(axes)
        cmd = 'MOVEP {0} {1} {2} {3}'.format(['', 'GROUP'][group],
                                             ['', 'STRICT'][strict],
                                             pos,
                                             ' '.join(map(str, axes)))
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
        # TODO: the grou
        axes = self._alias2axis(axes)
        cmd = 'PMOVE {0} {1} {2} {3}'.format(['', 'GROUP'][group],
                                             ['', 'STRICT'][strict],
                                             pos,
                                             ' '.join(map(str, axes)))
        self.send_cmd(cmd)

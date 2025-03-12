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
from functools import wraps

__all__ = ['ver122', 'ver1225', 'ver317', 'FirmwareVersion',
           'SUPPORTED_VERSIONS']

# TODO: Only versions supported @ ALBA Synchrotron
ver122 = {'SYSTEM': {'VER': 1.22,
                     'CONTROLLER': {'VER': 1.22,
                                    'DSP': 2.84,
                                    'FPGA': 0.03,
                                    'MCPU0': 0.2,
                                    'MCPU1': 0.2,
                                    'MCPU2': 1.125,
                                    # 'PCB': 0.07
                                    },
                     'DRIVER': {'VER': 1.22
                                },
                     },
          }

ver1225 = {'SYSTEM': {'VER': 1.225,
                      'CONTROLLER': {'VER': 1.225,
                                     'DSP': 2.85,
                                     'FPGA': 0.03,
                                     'MCPU0': 0.23,
                                     'MCPU1': 0.23,
                                     'MCPU2': 1.125,
                                     # 'PCB': 0.07
                                     },
                      'DRIVER': {'VER': 1.225
                                 },
                      },
           }

ver317 = {'SYSTEM': {'VER': 3.17,
                     'CONTROLLER': {'VER': 3.17,
                                    'DSP': 3.67,
                                    'FPGA': 1.0,
                                    'MCPU0': 1.19,
                                    'MCPU1': 1.19,
                                    'MCPU2': 1.125,
                                    # 'PCB': 1.0
                                    },
                     'DRIVER': {'VER': 3.17
                                },
                     },
          }

# TODO: mismatch between VER INFO and VER SAVED for 1.22 version.
SUPPORTED_VERSIONS = {'1.22': ver122,
                      '1.225': ver1225,
                      '3.17': ver317
                      }


def key_error(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except KeyError:
            return None
    return wrapped


# TODO: improve class to restrict info for component
class FirmwareVersion(dict):
    """
    Class to manage the different version numbers for the different components
    of the IcePAP system. A negative value means an error on the data.
    """
    def __init__(self, data, is_axis=False):
        super(FirmwareVersion, self).__init__()
        self.is_axis = is_axis
        for line in data:
            v = line.split(':', 2)
            length = len(line.split(line.lstrip())[0])
            # print 'length = %s' % l
            component = v[0].strip()
            try:
                value = float(v[1].strip())
            except Exception:
                value = -1.0
            # print component, value
            # manage date
            when = ''
            if len(v) > 2:
                when = v[2].strip()
            if length == 0:  # and component not in self.keys():
                self[component] = dict()
                self[component]['VER'] = (value, when)
                component0 = component
            elif length == 3:  # and component not in self['SYSTEM'].keys():
                self[component0][component] = dict()
                self[component0][component]['VER'] = (value, when)
                component1 = component
            elif length == 6:
                self[component0][component1][component] = (value, when)

    def __repr__(self):

        msg = '{0:<15s}:{1:>5s}\n'.format('SYSTEM', str(self.system))
        level = '   '
        sublevel = level * 2
        if not self.is_axis:
            # Not use field name does not work on python 2.6
            msg += '{0:}{1:<12s}:{2:>5s}\n'.format(level, 'CONTROLLER',
                                                   str(self.ctrl))
            msg += '{0:}{1:<9s}:{2:>5s}\n'.format(sublevel, 'DSP',
                                                  str(self.ctrl_dsp))
            msg += '{0:}{1:<9s}:{2:>5s}\n'.format(sublevel, 'FPGA',
                                                  str(self.ctrl_fpga))
            msg += '{0:}{1:<9s}:{2:>5s}\n'.format(sublevel, 'PCB',
                                                  str(self.ctrl_pcb))
            msg += '{0:}{1:<9s}:{2:>5s}\n'.format(sublevel, 'MCPU0',
                                                  str(self.ctrl_mcpu0))
            msg += '{0:}{1:<9s}:{2:>5s}\n'.format(sublevel, 'MCPU1',
                                                  str(self.ctrl_mcpu1))
            msg += '{0:}{1:<9s}:{2:>5s}\n'.format(sublevel, 'MCPU2',
                                                  str(self.ctrl_mcpu2))
        msg += '{0:}{1:<12s}:{2:>5s}\n'.format(level, 'DRIVER',
                                               str(self.driver))
        if self.is_axis:
            msg += '{0:}{1:<9s}:{2:>5s}\n'.format(sublevel, 'DSP',
                                                  str(self.driver_dsp))
            msg += '{0:}{1:<9s}:{2:>5s}\n'.format(sublevel, 'FPGA',
                                                  str(self.driver_fpga))
            msg += '{0:}{1:<9s}:{2:>5s}\n'.format(sublevel, 'PCB',
                                                  str(self.driver_pcb))
            msg += '{0:}{1:<9s}:{2:>5s}\n'.format(sublevel, 'IO',
                                                  str(self.driver_io))
        return msg

    def is_supported(self):
        """
        Returns is the system configuration is one of the supported versions.

        :return: bool
        """
        system = self._is_valid_system()
        ctrl = self._is_valid_ctrl()
        driver = self._is_valid_driver()
        return system and ctrl and driver

    def _is_valid_system(self):
        # print('supported system', str(self['SYSTEM']['VER'][0]))
        return str(self['SYSTEM']['VER'][0]) in list(SUPPORTED_VERSIONS.keys())

    @key_error
    def _is_valid_ctrl(self):
        if self._is_valid_system():
            _sys = str(self.system[0])
            _ctrl_ver = SUPPORTED_VERSIONS[_sys]['SYSTEM']['CONTROLLER']['VER']
            if self['SYSTEM']['CONTROLLER']['VER'][0] == _ctrl_ver:
                d = self['SYSTEM']['CONTROLLER']
                a = SUPPORTED_VERSIONS[_sys]['SYSTEM']['CONTROLLER']
                # Does not work on python 2.6
                # _d = {x: d[x][0] for x in d if x in a}
                _d = {}
                for x in d:
                    if x in a:
                        _d[x] = d[x][0]
                # print('supported ctrl:', a)
                # print('supported loaded:', _d)
                return a == _d
            else:
                return False
        else:
            return False

    @key_error
    def _is_valid_driver(self):
        if self._is_valid_system():
            _sys = str(self.system[0])
            _driver_ver = SUPPORTED_VERSIONS[_sys]['SYSTEM']['DRIVER']['VER']
            if self['SYSTEM']['DRIVER']['VER'][0] == _driver_ver:
                d = self['SYSTEM']['DRIVER']
                a = SUPPORTED_VERSIONS[_sys]['SYSTEM']['DRIVER']
                # Does not work on python 2.6
                # _d = {x: d[x][0] for x in d if x in a}
                _d = {}
                for x in d:
                    if x in a:
                        _d[x] = d[x][0]
                # print('supported driver:', a)
                # print('supported loaded:', _d)
                return a == _d
            else:
                return False
        else:
            return False

    @property
    @key_error
    def system(self):
        """
        Returns system version.

        :return: str
        """
        return self['SYSTEM']['VER']

    @property
    @key_error
    def ctrl(self):
        """
        Returns controller version.

        :return: str
        """
        return self['SYSTEM']['CONTROLLER']['VER']

    @property
    @key_error
    def ctrl_dsp(self):
        """
        Returns Controller DSP version.

        :return: str
        """
        return self['SYSTEM']['CONTROLLER']['DSP']

    @property
    @key_error
    def ctrl_fpga(self):
        """
        Returns Controller FPGA version.

        :return: str
        """
        return self['SYSTEM']['CONTROLLER']['FPGA']

    @property
    @key_error
    def ctrl_pcb(self):
        """
        Returns Controller FPGA version.

        :return: str
        """
        return self['SYSTEM']['CONTROLLER']['PCB']
    @property
    @key_error
    def ctrl_mcpu0(self):
        """
        Returns MCPU0 version.

        :return: str
        """
        return self['SYSTEM']['CONTROLLER']['MCPU0']

    @property
    @key_error
    def ctrl_mcpu1(self):
        """
        Returns MCPU1 version.

        :return: str
        """
        return self['SYSTEM']['CONTROLLER']['MCPU1']

    @property
    @key_error
    def ctrl_mcpu2(self):
        """
        Returns MCPU2 version.

        :return: str
        """
        return self['SYSTEM']['CONTROLLER']['MCPU2']

    @property
    @key_error
    def driver(self):
        """
        Returns driver version.

        :return: str
        """
        return self['SYSTEM']['DRIVER']['VER']

    @property
    @key_error
    def driver_dsp(self):
        """
        Returns driver DSP version.

        :return: str
        """
        return self['SYSTEM']['DRIVER']['DSP']

    @property
    @key_error
    def driver_fpga(self):
        """
        Returns driver FPGS version.

        :return: str
        """
        return self['SYSTEM']['DRIVER']['FPGA']

    @property
    @key_error
    def driver_pcb(self):
        """
        Returns driver PCB version.

        :return: (float, str)
        """
        return self['SYSTEM']['DRIVER']['PCB']

    @property
    @key_error
    def driver_io(self):
        """
        Returns driver PCB version.

        :return: (float, str)
        """
        return self['SYSTEM']['DRIVER']['IO']

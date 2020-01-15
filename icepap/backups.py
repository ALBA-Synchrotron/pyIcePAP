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

__all__ = ['IcePAPBackup']

import configparser
import time
import logging
import os
from icepap import IcePAPController


KEYNOTFOUNDIN1 = 'KeyNotFoundInBackup'       # KeyNotFound for dictDiff
KEYNOTFOUNDIN2 = 'KeyNotFoundInIcePAP'       # KeyNotFound for dictDiff
UNKNOWN = 'Unknown'


def dict_cfg(first, second):
    """
    Return a dict of keys that differ with another config object.  If a value
    is not found in one fo the configs, it will be represented by KEYNOTFOUND.
    @param first:   Fist configuration to diff.
    @param second:  Second configuration to diff.
    @return diff:   Dict of Key => (first.val, second.val)
    """

    diff = {}
    sd1 = set(first)
    sd2 = set(second)
    # Keys missing in the second dict
    for key in sd1.difference(sd2):
        diff[key] = (first[key], KEYNOTFOUNDIN2)
    # Keys missing in the first dict
    for key in sd2.difference(sd1):
        diff[key] = (KEYNOTFOUNDIN1, second[key])
    # Check for differences
    for key in sd1.intersection(sd2):
        value1 = first[key].upper().strip()
        value2 = second[key].upper().strip()
        if value1 != value2:
            diff[key] = (first[key], second[key])
    return diff


class IcePAPBackup:
    """
    Class to create/restore IcePAP backups based on Ethernet communication.
    """

    def __init__(self, host='', port=5000, timeout=3, cfg_file=''):
        log_name = '{0}.IcePAPBackup'.format(__name__)
        self.log = logging.getLogger(log_name)
        self._cfg_ipap = configparser.ConfigParser()
        self._cfg_bkp = None
        if cfg_file != '':
            self._cfg_bkp = configparser.ConfigParser()
            self._cfg_bkp.read(cfg_file)
            if host == '':
                host = self._cfg_bkp.get('SYSTEM', 'HOST')
            port = int(self._cfg_bkp.get('SYSTEM', 'PORT'))
        self._host = host
        self._port = port
        self._ipap = IcePAPController(host, port, timeout, auto_axes=True)

    def _add_axis(self, axis):
        """
        Method to add axis backup.
        :param axis: int
        :return: None
        """
        section_name = 'AXIS_{0}'.format(axis)
        self._cfg_ipap.add_section(section_name)
        # Active
        active = self._ipap[axis].active
        self._cfg_ipap.set(section_name, 'ACTIVE', str(active))
        if not active:
            self.log.warning('Driver {0} is not active, '
                             'some commands will fail.'.format(axis))
        # Version
        ver = self._ipap[axis].ver
        keys = list(ver['SYSTEM']['DRIVER'].keys())
        keys.sort()
        for key in keys:
            option = 'VER_{0}'.format(key)
            value = str(ver['SYSTEM']['DRIVER'][key][0])
            self._cfg_ipap.set(section_name, option, value)
        ver_drv = ver.driver[0]
        if ver_drv < 3:
            self.log.info('The version {0} does not support all command.'
                          'The script will generate warning'
                          'messages'.format(ver.driver))
        # Configuration
        ipap_cfg = self._ipap[axis].get_cfg()
        keys = list(ipap_cfg.keys())
        keys.sort()
        for key in keys:
            option = 'CFG_{0}'.format(key)
            value = ipap_cfg[key]
            self._cfg_ipap.set(section_name, option, value)

        # Attributes can fail on reading, but we save it anyway with UNKNOWN
        # value
        attrs = ['velocity', 'name', 'acctime', 'pcloop', 'indexer', 'infoa',
                 'infob', 'infoc', 'pos', 'pos_measure', 'pos_shftenc',
                 'pos_tgtenc', 'pos_ctrlenc', 'pos_encin', 'pos_inpos',
                 'pos_absenc', 'pos_motor', 'pos_sync', 'enc', 'enc_measure',
                 'enc_shftenc', 'enc_tgtenc', 'enc_ctrlenc', 'enc_encin',
                 'enc_inpos', 'enc_absenc', 'enc_motor', 'enc_sync', 'id']

        # Attributes can fail on reading because they are on version 3.17
        # This attributes won on the backup file if the version is < 3
        v3_attrs = ['cswitch', 'velocity_min', 'velocity_max', 'ecam',
                    'outpos', 'outpaux', 'syncpos', 'syncaux']

        attrs += v3_attrs
        attrs.sort()

        for attr in attrs:
            if attr in v3_attrs and ver_drv < 3:
                continue
            try:
                value = self._ipap[axis].__getattribute__(attr)
            except Exception as e:
                self.log.error('Error on reading axis {0} {1}: '
                               '{2}'.format(axis, attr, repr(e)))
                value = UNKNOWN
            self._cfg_ipap.set(section_name, attr, repr(value))

        # External Disable. Valid for FW < 3
        if ver_drv < 3:
            try:
                value = eval(self._ipap[axis].send_cmd('?DISDIS')[0])
            except Exception as e:
                self.log.error('Error on reading axis {0} {1}: '
                               '{2}'.format(axis, 'DISDIS', repr(e)))
                value = UNKNOWN
            self._cfg_ipap.set(section_name, 'DISDIS', repr(value))

    def _save_to_file(self, filename):
        abspath = os.path.abspath(filename)
        self.log.info('Saving backup on: {0}'. format(abspath))
        with open(abspath, 'w') as f:
            f.write('# File auto-generated by IcePAPBackup class.\n\n')
            self._cfg_ipap.write(f)

    def _add_system(self):
        section_name = 'SYSTEM'
        self._cfg_ipap.add_section(section_name)
        self._cfg_ipap.set(section_name, 'HOST', self._host)
        self._cfg_ipap.set(section_name, 'PORT', str(self._port))
        ver = str(self._ipap.ver['SYSTEM']['VER'][0])
        self._cfg_ipap.set(section_name, 'VERSION', ver)

    def _add_general(self):
        section_name = 'GENERAL'
        self._cfg_ipap.add_section(section_name)
        self._cfg_ipap.set(section_name, 'DATE', time.strftime('%Y/%m/%d'))
        self._cfg_ipap.set(section_name, 'TIME', time.strftime('%H:%M:%S +%z'))

    def _add_controller(self):
        section_name = 'CONTROLLER'
        self._cfg_ipap.add_section(section_name)
        # Version
        ver = self._ipap.ver
        keys = list(ver['SYSTEM']['CONTROLLER'].keys())
        keys.sort()
        for key in keys:
            option = 'VER_{0}'.format(key)
            value = str(ver['SYSTEM']['CONTROLLER'][key][0])
            self._cfg_ipap.set(section_name, option, value)

    def do_backup(self, filename='', axes=[], save=True, general=True):
        axes.sort()
        if general:
            self._add_general()
        self._add_system()
        self._add_controller()
        if len(axes) == 0:
            axes = self._ipap.axes
            axes.sort()
        for axis in axes:
            self._add_axis(axis)
        if save:
            self._save_to_file(filename)

    def do_check(self, axes=[]):
        self._cfg_bkp.pop('GENERAL')
        sections = self._cfg_bkp.sections()
        sections.pop(sections.index('SYSTEM'))
        sections.pop(sections.index('CONTROLLER'))
        for axis in axes:
            section = 'AXIS_{0}'.format(axis)
            try:
                sections.pop(sections.index(section))
            except Exception:
                raise ValueError('There is not backup for the axis '
                                 '{0}'.format(axis))
        if len(axes) > 0:
            for section in sections:
                self._cfg_bkp.pop(section)
        else:
            for section in sections:
                axis = int(section.split('_')[1])
                axes.append(axis)
        self.log.info('Checking IcePAP {0} axes: {1}'.format(self._host,
                                                             repr(axes)))
        self.do_backup(axes=axes, save=False, general=False)
        total_diff = {}
        if self._cfg_bkp == self._cfg_ipap:
            self.log.info('No differences found')
        else:
            sections = self._cfg_bkp.sections()
            for section in sections:
                diff = dict_cfg(self._cfg_bkp[section], self._cfg_ipap[
                    section])
                if len(diff) > 0:
                    total_diff[section] = diff
            self.log.info('Differences found: {0}'.format(repr(total_diff)))
        return total_diff

    def do_autofix(self, diff, force=False, skip_registers=[]):
        """
        Solve inconsistencies in IcePAP configuration registers.

        :param diff: Differences dictionary.
        :param force: Force overwrite of `enc` and `pos` register values.
        :param skip_registers: List of registers to do not overwrite
            when loading a saved configuration.
        :return:
        """
        self.active_axes(force=True)
        time.sleep(2)
        sections = list(diff.keys())
        axes = []
        for section in sections:
            if 'AXIS_' in section:
                axis = int(section.split('_')[1])
                axes.append(axis)
        axes.sort()
        for axis in axes:
            section = 'AXIS_{0}'.format(axis)
            registers = diff[section]
            for register in registers:
                if 'ver' in register:
                    continue
                if 'cfg' in register:
                    continue

                value_bkp, value_ipap = diff[section][register]

                if UNKNOWN in value_bkp:
                    continue

                # Check DISDIS configuration
                if register.lower() == 'disdis':
                    try:
                        if 'KeyNot' in value_bkp:
                            # Version backup > 3
                            value = diff[section]['cfg_extdisable'][0]
                            if value.lower() == 'none':
                                cmd = 'DISDIS 1'
                            else:
                                cmd = 'DISDIS 0'
                            self._ipap[axis].send_cmd(cmd)
                            self.log.info('Fixed axis {0} disdis '
                                          'configuration: cfg_extdisable({1})'
                                          ' -> {2}'.format(axis, value, cmd))
                        else:
                            # Version backup < 3:
                            value_bkp = eval(value_bkp)
                            self._ipap[axis].send_cmd('config')
                            value = ['Disable', 'NONE'][value_bkp]
                            cfg = 'EXTDISABLE {0}'.format(value)
                            self._ipap[axis].set_cfg(cfg)
                            cmd_str = 'config conf{0:03d}'.format(axis)
                            self._ipap[axis].send_cmd(cmd_str)

                            self.log.info('Fixed axis {0} disdis '
                                          'configuration: DISDIS {1} -> '
                                          'cfg_extdisable {2}'
                                          .format(axis, value_bkp, value))
                    except Exception as e:
                        if self._ipap[axis].mode != 'oper':
                            self._ipap[axis].send_cmd('config')
                        self.log.error('Cannot fix axis {0} disdis '
                                       'configuration: bkp({1}) icepap({2}).'
                                       ' Error {3}'.format(axis, value_bkp,
                                                           value_ipap, e))

                if 'KeyNot' in value_ipap or 'KeyNot' in value_bkp:
                    continue

                if register in skip_registers:
                    self.log.warning('Skip register by user '
                                     '{0}'.format(register))
                    continue

                if register.startswith('enc') and not force:

                    self.log.warning('Skip axis {0} {1}: bkp({2}) '
                                     'icepap({3})'.format(axis, register,
                                                          value_bkp,
                                                          value_ipap))
                    continue
                if register.startswith('pos'):
                    self.log.warning('Skip axis {0} {1}: bkp({2}) '
                                     'icepap({3})'.format(axis, register,
                                                          value_bkp,
                                                          value_ipap))
                    continue

                try:
                    value = eval(value_bkp)
                    if register == 'velocity':
                        acctime = self._ipap[axis].acctime
                        self._ipap[axis].velocity = value
                        self._ipap[axis].acctime = acctime
                    else:
                        self._ipap[axis].__setattr__(register, value)

                    self.log.info('Fixed axis {0} {1}: bkp({2}) '
                                  'icepap({3})'.format(axis, register,
                                                       value_bkp, value_ipap))
                except Exception as e:
                    self.log.error('Cannot fix axis {0} {1}: bkp({2}) '
                                   'icepap({3}). '
                                   'Error {4})'.format(axis, register,
                                                       value_bkp, value_ipap,
                                                       e))
        self.active_axes()

    def active_axes(self, axes=[], force=False):
        sections = self._cfg_bkp.sections()
        for section in sections:
            if section in ['GENERAL', 'SYSTEM', 'CONTROLLER']:
                continue
            axis = int(section.split('_')[1])
            if axes == [] or axis in axes:
                active = self._cfg_bkp.getboolean(section, 'ACTIVE')
                self._ipap[axis].send_cmd('config')
                if force:
                    cfg = 'ACTIVE YES'
                else:
                    cfg = 'ACTIVE {0}'.format(['NO', 'YES'][active])
                self.log.info('Axis {0}: {1}'.format(axis, cfg))
                self._ipap[axis].set_cfg(cfg)
                cmd = 'config conf{0:03d}'.format(axis)
                self._ipap[axis].send_cmd(cmd)

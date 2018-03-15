import configparser
import argparse
import time
import logging
from pyIcePAP import EthIcePAPController, Registers


KEYNOTFOUNDIN1 = 'KeyNotFoundInBackup'       # KeyNotFound for dictDiff
KEYNOTFOUNDIN2 = 'KeyNotFoundInIcePAP'       # KeyNotFound for dictDiff


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
        if first[key] != second[key]:
            diff[key] = (first[key], second[key])
    return diff


def print_diff(diff, level=0):
    keys = diff.keys()
    keys.sort()

    for key in keys:
        tab_level = ' ' * level
        if isinstance(diff[key], dict):
            line = '{0}{1}'.format(tab_level, key)
            print(line)
            next_level = level + 1
            print_diff(diff[key], next_level)
        else:
            val1 = diff[key][0]
            val2 = diff[key][1]
            line = '{0}{1:<20} {2:<20} {3}'.format(tab_level, key, val1, val2)
            print(line)


class IcePAPBackup(object):
    """
    Class to create/restore IcePAP backups based on Ethernet communication.
    """

    def __init__(self, host='', port=5000, timeout=3, cfg_file=''):
        self._cfg_ipap = configparser.ConfigParser()
        self._cfg_bkp = None
        if cfg_file != '':
            self._cfg_bkp = configparser.ConfigParser()
            self._cfg_bkp.read(cfg_file)
            host = self._cfg_bkp.get('SYSTEM', 'HOST')
            port = int(self._cfg_bkp.get('SYSTEM', 'PORT'))
        self._host = host
        self._port = port
        self._ipap = EthIcePAPController(host, port, timeout)

    def add_axis(self, axis):
        """
        Method to add axis backup.
        :param axis: int
        :return: None
        """
        section_name = 'AXIS_{0}'.format(axis)
        self._cfg_ipap.add_section(section_name)

        # Version
        ver = self._ipap[axis].ver
        keys = ver['SYSTEM']['DRIVER'].keys()
        keys.sort()
        for key in keys:
            option = 'VER_{0}'.format(key)
            value = str(ver['SYSTEM']['DRIVER'][key][0])
            self._cfg_ipap.set(section_name, option, value)

        # Configuration
        ipap_cfg = self._ipap[axis].get_cfg()
        keys = ipap_cfg.keys()
        keys.sort()
        for key in keys:
            option = 'CFG_{0}'.format(key)
            value = ipap_cfg[key]
            self._cfg_ipap.set(section_name, option, value)

        register = [Registers.AXIS, Registers.MEASURE, Registers.SHFTENC,
                    Registers.TGTENC, Registers.CTRLENC, Registers.ENCIN,
                    Registers.INPOS, Registers.ABSENC, Registers.MOTOR,
                    Registers.SYNC]
        register.sort()
        # Position Register
        for key in register:
            option = 'POS_{0}'.format(key)
            try:
                value = str(self._ipap[axis].get_pos(key))
            except Exception:
                value = 'NONE'
            self._cfg_ipap.set(section_name, option, value)

        # Encoder Register
        for key in register:
            option = 'ENC_{0}'.format(key)
            try:
                value = str(self._ipap[axis].get_enc(key))
            except Exception:
                value = 'NONE'
            self._cfg_ipap.set(section_name, option, value)

        # Limit switches configuration
        self._cfg_ipap.set(section_name, 'CSWITCH', self._ipap[axis].cswitch)

        # Name
        self._cfg_ipap.set(section_name, 'NAME', self._ipap[axis].name)

        # ID
        hw_id, sn_id = self._ipap[axis].id
        self._cfg_ipap.set(section_name, 'HW_ID', str(hw_id))
        self._cfg_ipap.set(section_name, 'SN_ID', str(sn_id))

        # Velocity
        value = str(self._ipap[axis].velocity)
        self._cfg_ipap.set(section_name, 'VELOCITY', value)
        value = str(self._ipap[axis].velocity_min)
        self._cfg_ipap.set(section_name, 'VELOCITY_MIN', value)
        value = str(self._ipap[axis].velocity_max)
        self._cfg_ipap.set(section_name, 'VELOCITY_MAX', value)

        # Acceleration time
        value = str(self._ipap[axis].acctime)
        self._cfg_ipap.set(section_name, 'ACCTIME', value)

        # Position close loop
        value = str(self._ipap[axis].pcloop)
        self._cfg_ipap.set(section_name, 'PCLOOP', value)

        # Indexer
        value = str(self._ipap[axis].indexer)
        self._cfg_ipap.set(section_name, 'INDEXER', value)

        # eCAM
        self._cfg_ipap.set(section_name, 'ECAM', self._ipap[axis].ecam)

        # InfoA
        value = ' '.join(self._ipap[axis].infoa)
        self._cfg_ipap.set(section_name, 'INFOA', value)

        # InfoB
        value = ' '.join(self._ipap[axis].infob)
        self._cfg_ipap.set(section_name, 'INFOB', value)

        # InfoC
        value = ' '.join(self._ipap[axis].infoa)
        self._cfg_ipap.set(section_name, 'INFOC', value)

        # OutPos
        value = ' '.join(self._ipap[axis].outpos)
        self._cfg_ipap.set(section_name, 'OUTPOS', value)

        # OutPaux
        value = ' '.join(self._ipap[axis].outpaux)
        self._cfg_ipap.set(section_name, 'OUTPAUX', value)

        # SyncPos
        value = ' '.join(self._ipap[axis].syncpos)
        self._cfg_ipap.set(section_name, 'SYNCPOS', value)

        # SyncAux
        value = ' '.join(self._ipap[axis].syncaux)
        self._cfg_ipap.set(section_name, 'SYNCAUX', value)

    def save_to_file(self, filename):
        with open(filename, 'w') as f:
            f.write('# File auto-generated by IcePAPBackup class.\n\n')
            self._cfg_ipap.write(f)

    def add_system(self):
        section_name = 'SYSTEM'
        self._cfg_ipap.add_section(section_name)
        self._cfg_ipap.set(section_name, 'HOST', self._host)
        self._cfg_ipap.set(section_name, 'PORT', str(self._port))
        ver = str(self._ipap.ver['SYSTEM']['VER'][0])
        self._cfg_ipap.set(section_name, 'VERSION', ver)

    def add_general(self):
        section_name = 'GENERAL'
        self._cfg_ipap.add_section(section_name)
        self._cfg_ipap.set(section_name, 'DATE', time.strftime('%Y/%m/%d'))
        self._cfg_ipap.set(section_name, 'TIME', time.strftime('%H:%M:%S +%z'))

    def add_controller(self):
        section_name = 'CONTROLLER'
        self._cfg_ipap.add_section(section_name)
        # Version
        ver = self._ipap.ver
        keys = ver['SYSTEM']['CONTROLLER'].keys()
        keys.sort()
        for key in keys:
            option = 'VER_{0}'.format(key)
            value = str(ver['SYSTEM']['CONTROLLER'][key][0])
            self._cfg_ipap.set(section_name, option, value)

    def do_backup(self, filename='', axes=[], save=True, general=True):
        axes.sort()
        if general:
            self.add_general()
        self.add_system()
        self.add_controller()
        if len(axes) == 0:
            axes = self._ipap.keys()
            axes.sort()
        for axis in axes:
            self.add_axis(axis)
        if save:
            self.save_to_file(filename)

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
        print('Checking IcePAP {0} axes: {1}'.format(self._host, repr(axes)))
        self.do_backup(axes=axes, save=False, general=False)
        if self._cfg_bkp == self._cfg_ipap:
            print('DONE')
        else:
            sections = self._cfg_bkp.sections()
            total_diff = {}
            for section in sections:
                diff = dict_cfg(self._cfg_bkp[section], self._cfg_ipap[
                    section])
                if len(diff) > 0:
                    total_diff[section] = diff
            line = 'Differences found:\n'
            line += '{0:<20} {1:<20} {2}'.format('Component', 'Backup',
                                                 'IcePAP')
            print(line)
            print_diff(total_diff)


def main():
    parse = argparse.ArgumentParser('IcePAP Backup scripts, base on ethernet '
                                    'communication')
    subps = parse.add_subparsers(help='commands')

    # Save backup command
    save_cmd = subps.add_parser('save', help='Command to save the '
                                             'configuration to a file')
    save_cmd.add_argument('host', help='IcePAP Host')
    save_cmd.add_argument('-p', '--port', default=5000, help='IcePAP port')
    save_cmd.add_argument('-t', '--timeout', default=3, help='Socket timeout')
    save_cmd.add_argument('filename', help='Output file name')
    save_cmd.add_argument('axes', nargs='*', help='Axes to save',
                          type=int, default=[])
    save_cmd.add_argument('-d', '--debug', action='store_true',
                          help='Activate log level DEBUG')

    save_cmd.set_defaults(which='save')

    # Check backup command
    check_cmd = subps.add_parser('check', help='Command to check the '
                                               'IcePAP configuration for a '
                                               'backup file')
    check_cmd.add_argument('filename', help='Backup file')
    check_cmd.add_argument('axes', nargs='*', help='Axes to save',
                           type=int, default=[])
    check_cmd.set_defaults(which='check')
    check_cmd.add_argument('-d', '--debug', action='store_true',
                          help='Activate log level DEBUG')

    args = parse.parse_args()
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    if args.which == 'save':
        ipap_bkp = IcePAPBackup(args.host, args.port, args.timeout)
        ipap_bkp.do_backup(args.filename, args.axes)
    elif args.which == 'check':
        ipap_bkp = IcePAPBackup(cfg_file=args.filename)
        ipap_bkp.do_check(args.axes)


if __name__ == '__main__':
    main()

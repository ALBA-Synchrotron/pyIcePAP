# !/usr/bin/env python
# -----------------------------------------------------------------------------
# This file is part of pyIcePAP (https://github.com/ALBA-Synchrotron/pyIcePAP)
#
# Copyright 2008-2017 CELLS / ALBA Synchrotron, Bellaterra, Spain
#
# Distributed under the terms of the GNU General Public License,
# either version 3 of the License, or (at your option) any later version.
# See LICENSE.txt for more info.
#
# You should have received a copy of the GNU General Public License
# along with pyIcePAP. If not, see <http://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------

import argparse
import logging
import logging.config
import time
import os
import sys
from .backups import IcePAPBackup, UNKNOWN
from .communication import EthIcePAPCommunication
from .programming import firmware_update
from .controller import EthIcePAPController

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
        'simple': {
            'format': '%(levelname)-8s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '',
            'mode': 'w',
            'encoding': 'utf-8',
            'formatter': 'verbose'
        }
    },
    'loggers': {
        'Application': {
            'handlers': ['console', 'file'],
            'propagate': True,
            'level': 'INFO',
        },
        'pyIcePAP': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        }
    }
}


def end(log, err_no=0):
    log_file = LOGGING_CONFIG['handlers']['file']['filename']
    log.info('Log saved on: {0}'.format(log_file))
    for h in log.handlers:
        h.flush()
    sys.exit(err_no)


def get_parser():
    parse = argparse.ArgumentParser('IcePAP scripts, base on ethernet '
                                    'communication')
    subps = parse.add_subparsers(help='commands')

    # -------------------------------------------------------------------------
    #                           Backup commands
    # -------------------------------------------------------------------------
    # Save backup command
    save_cmd = subps.add_parser('save', help='Command to save the '
                                             'configuration to a file')
    save_cmd.set_defaults(which='save')
    save_cmd.add_argument('host', help='IcePAP Host')
    save_cmd.add_argument('-p', '--port', default=5000, help='IcePAP port')
    save_cmd.add_argument('-t', '--timeout', default=3, help='Socket timeout')
    save_cmd.add_argument('--bkpfile', help='Output backup filename',
                          default='')
    save_cmd.add_argument('axes', nargs='*', help='Axes to save, default all',
                          type=int, default=[])
    save_cmd.add_argument('-d', '--debug', action='store_true',
                          help='Activate log level DEBUG')

    # Check backup command
    check_cmd = subps.add_parser('check', help='Command to check the '
                                               'IcePAP configuration for a '
                                               'backup file')
    check_cmd.set_defaults(which='check')
    check_cmd.add_argument('filename', help='Backup file')
    check_cmd.add_argument('axes', nargs='*', help='Axes to save, default all',
                           type=int, default=[])
    check_cmd.add_argument('-d', '--debug', action='store_true',
                           help='Activate log level DEBUG')
    check_cmd.add_argument('--host',
                           help='Use another IcePAP host instead of the '
                                'backup saved.',
                           default='')

    # -------------------------------------------------------------------------
    #                           Firmware commands
    # -------------------------------------------------------------------------
    # Update
    update_cmd = subps.add_parser('update', help='Command to change the '
                                                 'firmware version. It '
                                                 'creates a backup before to '
                                                 'change the FW')
    update_cmd.set_defaults(which='update')
    update_cmd.add_argument('host', help='IcePAP Host')
    update_cmd.add_argument('-p', '--port', default=5000, help='IcePAP port')
    update_cmd.add_argument('-t', '--timeout', default=3,
                            help='Socket timeout')
    update_cmd.add_argument('--bkpfile', help='Output backup filename',
                            default='')
    update_cmd.add_argument('--no-check',
                            help='Avoid the checking procedure after the '
                                 'update',
                            dest='nocheck')
    update_cmd.add_argument('fwfile', help='Firmware binary file')
    update_cmd.add_argument('-d', '--debug', action='store_true',
                            help='Activate log level DEBUG')

    # -------------------------------------------------------------------------
    #                           IcePAP commands
    # -------------------------------------------------------------------------
    # Send raw command
    send_cmd = subps.add_parser('send', help='Command to send IcePAP raw '
                                             'commands')

    send_cmd.set_defaults(which='send')
    send_cmd.add_argument('host', help='IcePAP Host')
    send_cmd.add_argument('-p', '--port', default=5000, help='IcePAP port')
    send_cmd.add_argument('-t', '--timeout', default=3, help='Socket timeout')
    send_cmd.add_argument('command', help='Raw command',
                          type=str)
    send_cmd.add_argument('-d', '--debug', action='store_true',
                          help='Activate log level DEBUG')
    # -------------------------------------------------------------------------
    return parse


def main():
    args = get_parser().parse_args()

    value = time.strftime('%Y%m%d_%H%m%S')
    log_file = '{0}_icepap_update.log'.format(value)
    log_file = os.path.abspath(log_file)
    LOGGING_CONFIG['handlers']['file']['filename'] = log_file
    logging.config.dictConfig(LOGGING_CONFIG)
    log = logging.getLogger('Application')

    # Save Command
    if args.which == 'save':
        if args.bkpfile == '':
            value = time.strftime('%Y%m%d_%H%m%S')
            args.bkpfile = '{0}_icepap_backup.cfg'.format(value)
        abspath = os.path.abspath(args.bkpfile)
        log.info('Saving backup on: {0}'.format(abspath))
        ipap_bkp = IcePAPBackup(args.host, args.port, args.timeout)
        ipap_bkp.do_backup(abspath, args.axes)

    # Check Command
    elif args.which == 'check':
        ipap_bkp = IcePAPBackup(host=args.host, cfg_file=args.filename)
        ipap_bkp.do_check(args.axes)

    # Send Command
    elif args.which == 'send':
        ipap_com = EthIcePAPCommunication(host=args.host, port=args.port,
                                          timeout=args.timeout)
        log.info(ipap_com.send_cmd(args.command))

    # Update Command
    elif args.which == 'update':
        if args.bkpfile == '':
            value = time.strftime('%Y%m%d_%H%m%S')
            args.bkpfile = '{0}_icepap_backup.cfg'.format(value)
        abspath = os.path.abspath(args.bkpfile)
        log.info('Updating {0} with firmware file {1}'.format(args.host,
                                                              args.fwfile))
        log.info('Saving backup on: {0}'.format(abspath))
        ipap_bkp = IcePAPBackup(host=args.host, port=args.port,
                                timeout=args.timeout)
        ipap_bkp.do_backup(abspath)
        if not firmware_update(args.host, args.fwfile, log):
            log.error('Errors on update firmware. Skipping active and check '
                      'driver procedure.')
            end(log, -1)

        log.info('Restore active drivers...')
        ipap_bkp = IcePAPBackup(cfg_file=abspath)
        ipap_bkp.active_axes()
        if args.nocheck:
            end(log)

        log.info('Checking registers....')
        diff = ipap_bkp.do_check()
        if len(diff) == 0:
            log.info('Checking DONE')
            end(log)

        log.info('Auto-fix differences')
        ipap_bkp.active_axes(force=True)
        time.sleep(2)
        ipap = EthIcePAPController(args.host)
        sections = diff.keys()
        sections.sort()
        for section in sections:
            if section in ['SYSTEM', 'CONTROLLER']:
                continue
            axis = int(section.split('_')[1])
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
                            ipap[axis].send_cmd(cmd)
                            log.info('Fixed axis {0} disdis configuration: '
                                     'cfg_extdisable({1}) ->'
                                     ' {2}'.format(axis, value, cmd))
                        else:
                            # Version backup < 3:
                            value_bkp = eval(value_bkp)
                            ipap[axis].send_cmd('config')
                            value = ['Disable', 'NONE'][value_bkp]
                            cfg = 'EXTDISABLE {0}'.format(value)
                            ipap[axis].set_cfg(cfg)
                            ipap[axis].send_cmd('config '
                                                'conf{0:03d}'.format(axis))

                            log.info('Fixed axis {0} disdis configuration: '
                                     'DISDIS {1} -> '
                                     'cfg_extdisable {2}'.format(axis,
                                                                 value_bkp,
                                                                 value))
                    except Exception as e:
                        if ipap[axis].mode != 'oper':
                            ipap[axis].send_cmd('config')
                        log.error('Can not fix axis {0} disdis configuration: '
                                  'bkp({1}) icepap({2}). '
                                  'Error {3}'.format(axis, value_bkp,
                                                     value_ipap, e))

                if 'KeyNot' in value_ipap or 'KeyNot' in value_bkp:
                    continue

                try:
                    value = eval(value_bkp)
                    if register == 'velocity':
                        acctime = ipap[axis].acctime
                        ipap[axis].velocity = value
                        ipap[axis].acctime = acctime
                    else:
                        ipap[axis].__setattr__(register, value)

                    log.info('Fixed axis {0} {1}: bkp({2}) '
                             'icepap({3})'.format(axis, register,
                                                  value_bkp, value_ipap))
                except Exception as e:
                    log.error('Can not fix axis {0} {1}: bkp({2}) '
                              'icepap({3}). '
                              'Error {4})'.format(axis, register,
                                                  value_bkp, value_ipap,
                                                  e))

        ipap_bkp.active_axes()
        end(log)


if __name__ == '__main__':
    main()

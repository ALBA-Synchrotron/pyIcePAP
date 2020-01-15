# !/usr/bin/env python
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

import argparse
import logging
import logging.config
import time
import os
import sys
from .backups import IcePAPBackup
from .communication import IcePAPCommunication
from .programming import firmware_update
from .__init__ import version


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
        'icepap': {
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
    desc = 'IcePAP scripts, base on ethernet communication\n'
    desc += 'Version: {}.\n'.format(version)
    epi = 'Documentation: https://alba-synchrotron.github.io/pyIcePAP-doc/\n'
    epi += 'Copyright 2008-2017 CELLS / ALBA Synchrotron, Bellaterra, Spain.'
    fmt = argparse.RawTextHelpFormatter
    parse = argparse.ArgumentParser(description=desc,
                                    formatter_class=fmt,
                                    epilog=epi)
    ver = '%(prog)s {0}'.format(version)
    parse.add_argument('--version', action='version', version=ver)
    subps = parse.add_subparsers(help='commands')

    # -------------------------------------------------------------------------
    #                           Backup commands
    # -------------------------------------------------------------------------
    # Save backup command
    save_cmd = subps.add_parser('save', help='Save the '
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
    check_cmd = subps.add_parser('check', help='Check the '
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
    update_cmd = subps.add_parser('update', help='Change the '
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
    update_cmd.add_argument('--force',
                            help='Force overwrite of enc/pos registers',
                            action='store_true')
    update_cmd.add_argument('fwfile', help='Firmware binary file')
    update_cmd.add_argument('-d', '--debug', action='store_true',
                            help='Activate log level DEBUG')

    # Autofix
    autofix_cmd = subps.add_parser('autofix', help='Autofix a driver '
                                                   'configuration')
    autofix_cmd.set_defaults(which='autofix')
    autofix_cmd.add_argument('host', help='IcePAP Host')
    autofix_cmd.add_argument('-p', '--port', default=5000, help='IcePAP port')
    autofix_cmd.add_argument('-t', '--timeout', default=3,
                             help='Socket timeout')
    autofix_cmd.add_argument('--bkpfile', help='Output backup filename',
                             default='')
    autofix_cmd.add_argument('--no-check',
                             help='Avoid the checking procedure after the '
                                  'update',
                             dest='nocheck')
    autofix_cmd.add_argument('--force',
                             help='Force overwrite of enc/pos registers',
                             action='store_true')
    autofix_cmd.add_argument('--skip-registers', nargs='*',
                             help='Registers will be skipped',
                             type=str, default=[],
                             dest='skip_registers')
    autofix_cmd.add_argument('loadfile', help='backup to load')
    autofix_cmd.add_argument('-d', '--debug', action='store_true',
                             help='Activate log level DEBUG')

    # -------------------------------------------------------------------------
    #                           IcePAP commands
    # -------------------------------------------------------------------------
    # Send raw command
    send_cmd = subps.add_parser('send', help='Send IcePAP raw '
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


def get_filename(host, command, filename='', log=False):
    value = time.strftime('%Y%m%d_%H%m%S')
    ext = ['cfg', 'log'][log]
    if host == '':
        host = 'icepap'
    new_filename = '{0}_{1}_{2}.{3}'.format(value, host, command, ext)
    if log or filename == '':
        filename = new_filename
    return os.path.abspath(filename)


def main():
    args = get_parser().parse_args()

    log_file = get_filename(args.host, args.which, log=True)
    LOGGING_CONFIG['handlers']['file']['filename'] = log_file
    logging.config.dictConfig(LOGGING_CONFIG)
    log = logging.getLogger('Application')

    # Save Command
    if args.which == 'save':
        abspath = get_filename(args.host, args.which, args.bkpfile)
        log.info('Saving backup on: {0}'.format(abspath))
        ipap_bkp = IcePAPBackup(args.host, args.port, args.timeout)
        ipap_bkp.do_backup(abspath, args.axes)

    # Check Command
    elif args.which == 'check':
        ipap_bkp = IcePAPBackup(host=args.host, cfg_file=args.filename)
        ipap_bkp.do_check(args.axes)

    # Send Command
    elif args.which == 'send':
        ipap_com = IcePAPCommunication(host=args.host, port=args.port,
                                       timeout=args.timeout)
        log.info(ipap_com.send_cmd(args.command))

    # Update Command
    elif args.which == 'update':
        abspath = get_filename(args.host, args.which, args.bkpfile)
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
            log.info('No differences found')
            end(log)

        log.info('Fixing differences')
        if args.force:
            log.info('Warning: Overwrite current enc/pos registers with saved'
                     ' values')
        ipap_bkp.do_autofix(diff, force=args.force)
        end(log)

    elif args.which == 'autofix':
        abspath = get_filename(args.host, args.which, args.bkpfile)
        log.info('Saving backup on: {0}'.format(abspath))
        ipap_bkp = IcePAPBackup(host=args.host, port=args.port,
                                timeout=args.timeout)
        ipap_bkp.do_backup(abspath)

        ipap_bkp = IcePAPBackup(host=args.host, cfg_file=args.loadfile)
        log.info('Checking registers....')
        diff = ipap_bkp.do_check()
        if len(diff) == 0:
            log.info('No differences found')
            end(log)

        log.info('Fixing differences')
        if args.force:
            log.info('Warning: Overwrite current enc/pos registers with saved'
                     ' values')
        ipap_bkp.do_autofix(diff, force=args.force,
                            skip_registers=args.skip_registers)
        end(log)


if __name__ == '__main__':
    main()

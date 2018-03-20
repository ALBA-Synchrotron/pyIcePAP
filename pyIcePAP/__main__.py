# !/usr/bin/env python
# -----------------------------------------------------------------------------
# This file is part of IcePAP (https://github.com/ALBA-Synchrotron/smaract)
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
from .backups import IcePAPBackup


def main():
    parse = argparse.ArgumentParser('IcePAP scripts, base on ethernet '
                                    'communication')
    subps = parse.add_subparsers(help='commands')

    # -------------------------------------------------------------------------
    #                           Backup commands
    # -------------------------------------------------------------------------
    # Save backup command
    save_cmd = subps.add_parser('save', help='Command to save the '
                                             'configuration to a file')
    save_cmd.add_argument('host', help='IcePAP Host')
    save_cmd.add_argument('-p', '--port', default=5000, help='IcePAP port')
    save_cmd.add_argument('-t', '--timeout', default=3, help='Socket timeout')
    save_cmd.add_argument('filename', help='Output file name')
    save_cmd.add_argument('axes', nargs='*', help='Axes to save, default all',
                          type=int, default=[])
    save_cmd.add_argument('-d', '--debug', action='store_true',
                          help='Activate log level DEBUG')

    save_cmd.set_defaults(which='save')

    # Check backup command
    check_cmd = subps.add_parser('check', help='Command to check the '
                                               'IcePAP configuration for a '
                                               'backup file')
    check_cmd.add_argument('filename', help='Backup file')
    check_cmd.add_argument('axes', nargs='*', help='Axes to save, default all',
                           type=int, default=[])
    check_cmd.set_defaults(which='check')
    check_cmd.add_argument('-d', '--debug', action='store_true',
                           help='Activate log level DEBUG')
    check_cmd.add_argument('--host',
                           help='Use another IcePAP host instead of the '
                                'backup saved.',
                           default='')

    # -------------------------------------------------------------------------
    #                           Firmware commands
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    #                           IcePAP commands
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    args = parse.parse_args()
    if args.debug:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(level=level,
                        format='%(asctime)s - %(name)s - %(levelname)s - '
                               '%(message)s')
    if args.which == 'save':
        ipap_bkp = IcePAPBackup(args.host, args.port, args.timeout)
        ipap_bkp.do_backup(args.filename, args.axes)
    elif args.which == 'check':
        ipap_bkp = IcePAPBackup(host=args.host, cfg_file=args.filename)
        ipap_bkp.do_check(args.axes)


if __name__ == '__main__':
    main()

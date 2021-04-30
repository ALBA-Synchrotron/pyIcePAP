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
from .cli import cli

# LOGGING_CONFIG = {
#     'version': 1,
#     'disable_existing_loggers': True,
#     'formatters': {
#         'verbose': {
#             'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
#         },
#         'simple': {
#             'format': '%(levelname)-8s %(message)s'
#         },
#     },
#     'handlers': {
#         'console': {
#             'level': 'INFO',
#             'class': 'logging.StreamHandler',
#             'formatter': 'simple'
#         },
#         'file': {
#             'level': 'INFO',
#             'class': 'logging.FileHandler',
#             'filename': '',
#             'mode': 'w',
#             'encoding': 'utf-8',
#             'formatter': 'verbose'
#         }
#     },
#     'loggers': {
#         'Application': {
#             'handlers': ['console', 'file'],
#             'propagate': True,
#             'level': 'INFO',
#         },
#         'icepap': {
#             'handlers': ['file'],
#             'level': 'INFO',
#             'propagate': True,
#         }
#     }
# }
#
#
# def end(log, err_no=0):
#     log_file = LOGGING_CONFIG['handlers']['file']['filename']
#     log.info('Log saved on: {0}'.format(log_file))
#     for h in log.handlers:
#         h.flush()
#     sys.exit(err_no)
#
#
# def get_parser():
#     desc = 'IcePAP scripts, base on ethernet communication\n'
#     desc += 'Version: {}.\n'.format(version)
#     epi = 'Documentation: https://alba-synchrotron.github.io/pyIcePAP-doc/\n'
#     epi += 'Copyright 2008-2017 CELLS / ALBA Synchrotron, Bellaterra, Spain.'
#     fmt = argparse.RawTextHelpFormatter
#     parse = argparse.ArgumentParser(description=desc,
#                                     formatter_class=fmt,
#                                     epilog=epi)
#     ver = '%(prog)s {0}'.format(version)
#     parse.add_argument('--version', action='version', version=ver)
#     subps = parse.add_subparsers(help='commands')
#
#
# def get_filename(host, command, filename='', log=False):
#     value = time.strftime('%Y%m%d_%H%m%S')
#     ext = ['cfg', 'log'][log]
#     if host == '':
#         host = 'icepap'
#     new_filename = '{0}_{1}_{2}.{3}'.format(value, host, command, ext)
#     if log or filename == '':
#         filename = new_filename
#     return os.path.abspath(filename)


def main():
    # log_file = get_filename(args.host, args.which, log=True)
    # LOGGING_CONFIG['handlers']['file']['filename'] = log_file
    # logging.config.dictConfig(LOGGING_CONFIG)
    # log = logging.getLogger('Application')
    #
    # # Send Command
    # if args.which == 'send':
    #     ipap_com = IcePAPCommunication(host=args.host, port=args.port,
    #                                    timeout=args.timeout)
    #     log.info(ipap_com.send_cmd(args.command))
    cli()


if __name__ == '__main__':
    main()

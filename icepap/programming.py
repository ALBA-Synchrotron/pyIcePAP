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
import sys
import time
import array
from icepap import IcePAPController

__all__ = ['firmware_update']

# TODO: Review downgrade from 1.225 to 1.22 (MCPU<X> components not updated)


def _monitor(ice):
    wait = True
    try:
        if not ice.connected:
            raise RuntimeError('No connection available')
        status = ice.get_prog_status()
        if status[0].upper() != 'DONE':
            _progress_bar(float(status[-1]), 100, 'Updating IcePAP firmware')
            time.sleep(.2)
        else:
            wait = False
    except RuntimeError:
        print('\nConnection lost, waiting for reconnection...')
        while not ice.connected:
            time.sleep(0.5)
        print('Reconnected!')
    finally:
        return wait


def load_firmware(ice, filename):
    """
    Loads code firmware contained in filename to system master controller
    internal flash memory (tocho file).

    :param ice: IcePAPController object.
    :param filename: firmware code.
    """
    if filename:
        with open(filename, 'rb') as f:
            data = f.read()
        data = array.array('H', data)
        ice.sprog(saving=True)
        ice._comm.send_binary(ushort_data=data)

    # Avoid timeout while ICEPAP is saving the file to master
    time.sleep(5)
    # print('New firmware loaded to master')


def _progress_bar(count, total, status=''):
    bar_len = 60
    filled_len = int(round(bar_len * count / float(total)))

    percents = round(100.0 * count / float(total), 1)
    bar = '=' * filled_len + '-' * (bar_len - filled_len)

    sys.stdout.write('[%s] %s%s < %s >\r' % (bar, percents, '%', status))
    sys.stdout.flush()
    # As suggested by Rom Ruben (see: http://stackoverflow.com/questions/
    # 3173320/text-progress-bar-in-the-console/
    # 27871113#comment50529068_27871113)


def install_firmware(ice, component='ALL', force=False, saving=False,
                     filename=None):
    """
    Update icepap firmware. If filename is not supplied, the firmware
    update will use the code stored in the system master controller.

    :param ice: IcePAPController object.
    :param component: { board adress | DRIVERS | CONTROLLERS| ALL }
    :param force: Force overwrite regardless of being idential versions.
    :param saving: Saves firmware into master board flash.
    :param filename: firmware code.
    """

    if filename:
        with open(filename, 'rb') as f:
            data = f.read()
        data = array.array('H', data)
        # from external firmware code
        ice.sprog(component, force=force, saving=saving)
        # TODO: make the method public
        ice._comm.send_binary(ushort_data=data)
    else:
        ice.prog(component, force=force)


# TODO: Define entry point for system_update method

def firmware_update(hostname, filename, log):
    """
    Installs firmware stored in master memory to ALL system components.

    :param hostname: Icepap host
    :param filename: Firmware filename
    :param log: Logger object
    """
    ice = IcePAPController(hostname)

    try:
        curr_ver = ice.ver['SYSTEM']['VER'][0]
    except Exception as e:
        log.error('Can not read the current version. {}'.format(e))
        curr_ver = -1
    log.info('Current firmware version is {}'.format(curr_ver))
    ice.mode = 'prog'
    load_firmware(ice, filename)
    log.info('Firmware "{}" loaded to master.'.format(filename))
    try:
        new_ver = ice.ver_saved.system[0]
    except Exception:
        new_ver = -1

    log.info('Installing version {}'.format(new_ver))
    if curr_ver < 3.17:

        install_firmware(ice, 'ALL', force=True)
        install_firmware(ice, 'MCPU0')
        install_firmware(ice, 'MCPU1')
        install_firmware(ice, 'MCPU2')
    else:
        install_firmware(ice, 'ALL', force=True)

    # wait process to finish
    wait = True
    while wait:
        wait = _monitor(ice)
        time.sleep(0.5)
    ice.reboot()
    print('')
    # wait reboot to finish
    for i in range(120):
        _progress_bar(i+1, 120, 'Rebooting IcePAP')
        time.sleep(1)
    print('')
    ice = IcePAPController(hostname)
    ice.mode = 'oper'
    if ice.mode.lower() != 'oper':
        log.error('[ERROR: It was not possible to set mode oper!!!]')
        return False
    log.info('Change firmware DONE')
    return True

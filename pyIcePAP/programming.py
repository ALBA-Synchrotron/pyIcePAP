import sys
import time
import array
from future import *
from pyIcePAP import EthIcePAPController

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
        print '\nConnection lost, waiting for reconnection...'
        while not ice.connected:
            time.sleep(0.5)
        print 'Reconnected!'
    finally:
        return wait


def load_firmware(ice, filename):
    """
    Loads code firmware contained in filename to system master controller
    internal flash memory (tocho file).

    :param ice: IcePAPController object.
    :param filename: firmware code.
    :return: None
    """
    if filename:
        with open(filename, 'rb') as f:
            data = f.read()
        data = array.array('H', data)
        ice.sprog(saving=True)
        ice._comm.send_binary(ushort_data=data)

    # Avoid timeout while ICEPAP is saving the file to master
    time.sleep(5)
    #print('New firmware loaded to master')


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
    :return: None
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
def firmware_update(hostname, filename):
    ice = EthIcePAPController(hostname)

    curr_ver = ice.check_version()
    print('Current firmware version is {}'.format(curr_ver))

    load_firmware(ice, filename)
    print('Firmware "{}" loaded to master.'.format(filename))
    new_ver = ice.ver_saved.system[0]

    print('Installing version {}'.format(new_ver))
    install_firmware(ice, 'ALL', force=True)

    # wait process to finish
    wait = True
    while wait:
        wait = _monitor(ice)
        time.sleep(0.5)

    if curr_ver < 3.17:
        install_firmware(ice, 'ALL', force=True)
        install_firmware(ice, 'MCPU0')
        install_firmware(ice, 'MCPU1')
        install_firmware(ice, 'MCPU2')

    ice.reboot()
    # wait reboot to finish
    time.sleep(5)
    wait = True
    while wait:
        wait = _monitor(ice)
        time.sleep(0.5)
    print('\nwaiting...')
    time.sleep(35)
    print('[DONE]')

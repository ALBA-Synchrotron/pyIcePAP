import functools
import unittest.mock as mock
import socket
import errno
import contextlib

from icepap import FirmwareVersion


VER = '''\
0:?VER $
SYSTEM       :  3.23 : Mon Feb 17 12:44:04 2020
   CONTROLLER:  3.23
      DSP    :  3.89 : Mon Feb 17 12:42:47 2020
      FPGA   :  2.00 : Thu Nov 29 17:07:00 2018
      PCB    :  1.00
      MCPU0  :  0.20
      MCPU1  :  0.20
      MCPU2  :  1.125
   DRIVER    :  3.23
$'''

EXPECTED_VER = FirmwareVersion(VER.split("\n")[1:-1])

ENCODING = 'latin-1'

STD_AXIS = dict(
    pos_axis=55, fpos_axis=55,
    status='0x00205013', fstatus='0x00205013', power='ON',
    active='YES', mode='OPER', alarm='NO',
    config='toto@pc1_2019/06/17_12:51:24',
    stopcode='0x0000', vstopcode='No abnormal stop condition',
    warning='NONE', wtemp='45', cswitch='NORMAL',
    id_hw='0008.028E.EB82', id_sn='4960', post='0', auxps='ON',
    meas_vcc='80.2165', meas_i='0.00545881',
    meas_ia='-0.00723386', meas_ib='-0.000653267',
    meas_ic='0', meas_r='-6894.35', meas_ra='-3797.74',
    meas_rb='-3797.74',
    meas_rc='ERROR Current too low to take the measure',
    enc_axis=100, velocity=100, velocity_max=3000,
    velocity_min=2, velocity_default=50, acctime=0.1,
    acctime_default=0.01, acctime_steps=30, pcloop='ON',
    indexer='INTERNAL',
    infoa='HIGH NORMAL', infob='HIGH NORMAL',
    infoc='HIGH INVERTED', outpos='MOTOR NORMAL',
    outpaux='LOW NORMAL', syncpos='AXIS NORMAL',
    syncaux='ENABLED NORMAL'
)


def patch_socket(mock):
    axes = {
        '1': dict(STD_AXIS, addr='1', name='th'),
        '5': dict(STD_AXIS, addr='5', name='tth', pos_axis=-3, fpos_axis=-3),
        '151': dict(STD_AXIS, addr='151', name='chi',
                    pos_axis=-1000, fpos_axis=-1000, power='OFF',
                    velocity=1002, acctime=0.25),
        '152': dict(STD_AXIS, addr='152', name='phi',
                    pos_axis=1000, fpos_axis=1000, power='OFF'),
        '153': dict(STD_AXIS, addr='153', name='mu',
                    pos_axis=1000, fpos_axis=1000)
    }
    racks = {
        '0': dict(rid='0008.0153.F797', stat='0x11 0x11', rtemp='30.1'),
        '15': dict(rid='0008.020B.1028', stat='0x03 0x01', rtemp='29.5')
    }

    last_send = [None]

    def get_axis_question(cmd):
        axis, cmd = cmd.split(':?', 1)
        if axis in axes:
            msg = axes[axis][cmd.lower()]
        else:
            msg = 'ERROR Board is not present in the system'
        cmd_reply = cmd.split('_')[0]
        return '{}:?{} {}\n'.format(axis, cmd_reply, msg)

    def get_multi_axis_question(cmd):
        args = cmd.split()
        cmd = args[0][1:]
        if cmd.upper() in {'ACCTIME', 'VELOCITY'}:
            axes_list = args[2:]
        else:
            axes_list = args[1:]
        pos = [str(axes[axis][cmd.lower()]) for axis in axes_list]
        cmd_reply = cmd.split('_')[0]
        return '?{} {}\n'.format(cmd_reply, ' '.join(pos))

    def process_read_cmd(cmd):
        if cmd == '0:?VER INFO':
            result = VER
        elif cmd == '?SYSSTAT':
            result = '?SYSSTAT 0x8001\n'
        elif cmd == '?MODE':
            result = '?MODE OPER\n'

        elif cmd.startswith('?SYSSTAT '):
            rid = cmd.split()[-1]
            rack = racks.get(rid, dict(stat='0x00 0x00'))
            result = '?SYSSTAT {}\n'.format(rack['stat'])
        elif '?RID' in cmd:
            params = cmd.split()[1:]
            rid = [racks[rack]['rid'] for rack in params]
            result = '?RID {}\n'.format(' '.join(rid))
        elif '?RTEMP' in cmd:
            params = cmd.split()[1:]
            rtemp = [racks[rack]['rtemp'] for rack in params]
            result = '?RTEMP {}\n'.format(' '.join(rtemp))

        elif ':?' in cmd:
            result = get_axis_question(cmd)
        elif '?' in cmd:
            result = get_multi_axis_question(cmd)

        return result

    def set_axis(cmd):
        axis, cmd = cmd.split(':', 1)
        register, value = cmd.split(' ', 1)
        register = register.lower()
        if register in ['infoa', 'infob', 'infoc', 'outpos', 'outpaux',
                        'syncpos', 'syncaux']:
            value = value.split()
            if len(value) == 1:
                value.append('NORMAL')
            value = ' '.join(value)
        if axis in axes:
            axes[axis][register] = value
            msg = 'OK'
        else:
            msg = 'ERROR Board is not present in the system'
        cmd_reply = cmd.split('_')[0]
        return '{}:{} {}\n'.format(axis, cmd_reply, msg)

    def set_multi_axis(cmd):
        pass

    def process_write_cmd(cmd):
        cmd = cmd.replace('#', '')
        if ':' in cmd:
            result = set_axis(cmd)
        else:
            result = set_multi_axis(cmd)
        return result

    def connect(addr):
        host, port = addr
        if not host.startswith('127.0.0.1'):
            raise socket.gaierror(-2, 'Name or service not known')
        if port != 5000:
            raise socket.error(111, 'Connection refused')

    def connect_ex(sock, addr):
        host, port = addr
        if not host.startswith('icepap'):
            raise socket.gaierror(-2, 'Name or service not known')
        sock._addr = addr
        return errno.EINPROGRESS

    def getsockopt(sock, level, option):
        if level == socket.SOL_SOCKET and option == socket.SO_ERROR:
            if sock._addr[1] != 5000:
                return errno.ECONNREFUSED
            return 0

    def sendall(data):
        # sockets receive bytes
        cmd = data.decode(ENCODING)
        last_send[0] = cmd
        return len(cmd)

    def recv(size):
        cmd = last_send[0]
        last_send[0] = None
        cmd = cmd.upper().strip()

        # Position registers
        if 'OUTPOS' not in cmd and 'SYNCPOS' not in cmd:
            cmd = cmd.replace('POS AXIS', 'POS_AXIS')
            cmd = cmd.replace('POS SHFTENC', 'POS_AXIS')
            cmd = cmd.replace('POS TGTENC', 'POS_AXIS')
            cmd = cmd.replace('POS CTRLENC', 'POS_AXIS')
            cmd = cmd.replace('POS ENCIN', 'POS_AXIS')
            cmd = cmd.replace('POS INPOS', 'POS_AXIS')
            cmd = cmd.replace('POS ABSENC', 'POS_AXIS')
            cmd = cmd.replace('POS MOTOR', 'POS_AXIS')
            cmd = cmd.replace('POS SYNC', 'POS_AXIS')

        # Encoder registers
        cmd = cmd.replace('ENC AXIS', 'ENC_AXIS')
        cmd = cmd.replace('ENC SHFTENC', 'ENC_AXIS')
        cmd = cmd.replace('ENC TGTENC', 'ENC_AXIS')
        cmd = cmd.replace('ENC CTRLENC', 'ENC_AXIS')
        cmd = cmd.replace('ENC ENCIN', 'ENC_AXIS')
        cmd = cmd.replace('ENC INPOS', 'ENC_AXIS')
        cmd = cmd.replace('ENC ABSENC', 'ENC_AXIS')
        cmd = cmd.replace('ENC MOTOR', 'ENC_AXIS')
        cmd = cmd.replace('ENC SYNC', 'ENC_AXIS')

        # ID
        cmd = cmd.replace('ID HW', 'ID_HW')
        cmd = cmd.replace('ID SN', 'ID_SN')

        # Measurement registers
        cmd = cmd.replace('MEAS VCC', 'MEAS_VCC')
        cmd = cmd.replace('MEAS I', 'MEAS_I')
        cmd = cmd.replace('MEAS IA', 'MEAS_IA')
        cmd = cmd.replace('MEAS IB', 'MEAS_IB')
        cmd = cmd.replace('MEAS IC', 'MEAS_IC')
        cmd = cmd.replace('MEAS R', 'MEAS_R')
        cmd = cmd.replace('MEAS RA', 'MEAS_RA')
        cmd = cmd.replace('MEAS RB', 'MEAS_RB')
        cmd = cmd.replace('MEAS RC', 'MEAS_RC')
        cmd = cmd.replace('MEAS T', 'MEAS_T')
        cmd = cmd.replace('MEAS RT', 'MEAS_RT')

        # Velocity
        cmd = cmd.replace('VELOCITY MIN', 'VELOCITY_MIN')
        cmd = cmd.replace('VELOCITY MAX', 'VELOCITY_MAX')
        cmd = cmd.replace('VELOCITY DEFAULT', 'VELOCITY_DEFAULT')
        cmd = cmd.replace('VELOCITY CURRENT', 'VELOCITY')

        # Acceleration time
        cmd = cmd.replace('ACCTIME DEFAULT', 'ACCTIME_DEFAULT')
        cmd = cmd.replace('ACCTIME STEPS', 'ACCTIME_STEPS')

        if '?' in cmd:
            result = process_read_cmd(cmd)
        else:
            result = process_write_cmd(cmd)

        # sockets return bytes
        return result.encode(ENCODING)

        process_read_cmd()

    mock.return_value.recv = recv
    mock.return_value.sendall = sendall
    mock.return_value.connect = connect
    mock.return_value.connect_ex = lambda *a: connect_ex(
        mock.socket.return_value, *a)
    mock.return_value.getsockopt = lambda *a: getsockopt(
        mock.socket.return_value, *a)


def patch_select(mock):
    def select(r, w, e, timeout=None):
        return r, w, e
    mock.select = select


def select_context():
    return mock.patch('icepap.tcp.select')


def socket_context():
    return mock.patch('icepap.tcp.socket.socket')


@contextlib.contextmanager
def mock_socket():
    with socket_context() as mock_sock, select_context() as mock_sel:
        patch_socket(mock_sock)
        patch_select(mock_sel)
        yield mock_sock, mock_sel

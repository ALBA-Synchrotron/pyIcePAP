import functools
import unittest.mock as mock
import socket

VER = '''\
0:?VER $
SYSTEM       :  3.17 : Tue Feb 16 10:57:37 2016
   CONTROLLER:  3.17
      DSP    :  3.67 : Mon Dec 14 13:22:03 2015
      FPGA   :  1.00 : Tue Jan 21 19:33:00 2014
      PCB    :  1.00
      MCPU0  :  1.19
      MCPU1  :  1.19
      MCPU2  :  1.125
   DRIVER    :  3.17
$'''

ENCODING = 'latin-1'


def patch_socket(mock):
    axes = {
        '1': dict(addr='1', name='th', pos_axis=55, fpos_axis=55,
                  status='0x00205013', fstatus='0x00205013', power='ON'),
        '5': dict(addr='5', name='tth', pos_axis=-3, fpos_axis=-3,
                  status='0x00205013', fstatus='0x00205013', power='ON'),
        '151': dict(addr='151', name='chi', pos_axis=-1000, fpos_axis=-1000,
                    status='0x00205013', fstatus='0x00205013', power='OFF'),
        '152': dict(addr='152', name='phi', pos_axis=1000, fpos_axis=1000,
                    status='0x00205013', fstatus='0x00205013', power='OFF')
    }
    racks = {
        '0': dict(rid='0008.0153.F797', stat='0x11 0x11', rtemp='30.1'),
        '15': dict(rid='0008.020B.1028', stat='0x03 0x01', rtemp='29.5')
    }

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
        pos = [str(axes[axis][cmd.lower()]) for axis in args[1:]]
        cmd_reply = cmd.split('_')[0]
        return '?{} {}\n'.format(cmd_reply, ' '.join(pos))

    last_send = [None]

    def connect(addr):
        host, port = addr
        if not host.startswith('icepap'):
            raise socket.gaierror(-2, 'Name or service not known')
        if port != 5000:
            raise socket.error(111, 'Connection refused')

    def sendall(data):
        # sockets receive bytes
        last_send[0] = data.decode(ENCODING)

    def recv(size):
        cmd = last_send[0]
        last_send[0] = None
        cmd = cmd.upper().strip().replace('POS AXIS', 'POS_AXIS')
        # answer = ('#' in cmd) or ('?' in cmd)

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
        # sockets return bytes
        return result.encode(ENCODING)

    mock.return_value.recv = recv
    mock.return_value.sendall = sendall
    mock.return_value.connect = connect


def socket_context():
    return mock.patch('pyIcePAP.communication.socket')


def protect_socket(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        with socket_context() as mock_sock:
            patch_socket(mock_sock)
            return f(*args, **kwargs)
    return wrapper

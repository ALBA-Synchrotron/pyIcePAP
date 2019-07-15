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
                  indexer='INTERNAL'),
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
        pos = [str(axes[axis][cmd.lower()]) for axis in args[1:]]
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
        register, value = cmd.split()
        if axis in axes:
            axes[axis][register.lower()] = value
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
        if not host.startswith('icepap'):
            raise socket.gaierror(-2, 'Name or service not known')
        if port != 5000:
            raise socket.error(111, 'Connection refused')

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


def socket_context():
    return mock.patch('pyIcePAP.communication.socket')


def protect_socket(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        with socket_context() as mock_sock:
            patch_socket(mock_sock)
            return f(*args, **kwargs)
    return wrapper

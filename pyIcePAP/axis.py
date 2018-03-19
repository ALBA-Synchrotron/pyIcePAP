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

import weakref
import struct
from future import *
from .vdatalib import vdata, ADDRUNSET, POSITION, PARAMETER, SLOPE
from .utils import State


class IcePAPAxis(object):
    """
    IcePAP axis class. Contains the common IcePAP ASCii API for any
    IcePAP axis. The methods here implemented correspond to those
    at the axis level.
    """

    def __init__(self, ctrl, axis_nr):
        ref = weakref.ref(ctrl)
        self._ctrl = ref()
        self._axis_nr = axis_nr
        rack_id = int(self._axis_nr / 10)
        axis_id = int(self._axis_nr % 10)
        self._str_id = '{0:x}{1:x}'.format(rack_id, axis_id)

        # if self._axis_nr != self.addr:
        #     msg = 'Initialization error: axis_nr {0} != adr {1}'.format(
        #         self._axis_nr, self.addr)
        #     raise RuntimeError(msg)

    @staticmethod
    def get_ushort_list(ldata, dtype='FLOAT'):
        dtype = dtype.upper()
        if dtype == 'DWORD':
            pack_format = '{0}i'
            factor = 2
        elif dtype == 'FLOAT':
            pack_format = '{0}f'
            factor = 2
        elif dtype == 'DFLOAT':
            pack_format = '{0}d'
            factor = 4
        elif dtype == 'BYTE':
            pack_format = '{0}b'
            factor = 0.5
        else:
            raise ValueError('dtype is not valid')

        data_len = len(ldata)
        data_pck = struct.pack(pack_format.format(data_len), *ldata)

        unpack_format = '{0}H'.format(int(data_len * factor))
        lushorts = struct.unpack(unpack_format, data_pck)
        return lushorts

    @staticmethod
    def get_dump_values(raw_table, dtype='FLOAT'):
        # TODO: use the memory map.
        values = []
        for raw_value in raw_table:
            try:
                id_value, _, value = raw_value.strip().split(':')
            except Exception:
                raise RuntimeError('There are not values loaded on the '
                                   'ecam table.')
            values.append(float(value))
            last_id_data, len_data = id_value.split('/')
        last_id_data = int(last_id_data)
        len_data = int(len_data)
        return values, last_id_data, len_data

    def _get_dump_table(self, cmd, dtype='FLOAT'):
        MAX_SUBSET_SIZE = 200
        table = []
        start_pos = 0
        while True:
            raw_table = self.send_cmd(cmd.format(MAX_SUBSET_SIZE, start_pos))
            values, last_id, len_data = self.get_dump_values(raw_table,
                                                             dtype)
            table += values
            # The data dumped from list position table has a bug the total
            # len is not correct
            if 'LISTDAT' in cmd.upper():
                len_data -= 1
            if int(last_id) == int(len_data):
                break
            start_pos = last_id + 1
        return table

    @property
    def addr(self):
        """
        Get the rack number and axis number.
        IcePAP user manual pag. 49
        :return: (int, int)
        """
        ans = self.send_cmd('?ADDR')[0].strip()
        rack_nr = int(ans[0], 16)
        axis_nr = int(ans[1], 16)
        return rack_nr, axis_nr

    @property
    def active(self):
        """
        Get if the axis is active.
        IcePAP user manual pag. 47
        :return: bool
        """
        ans = self.send_cmd('?ACTIVE')[0].upper()
        return ans == 'YES'

    @property
    def mode(self):
        """
        Return the current mode of the axis: CONFIG, OPER, PROG, TEST, FAIL
        IcePAP user manual pag. 91
        :return: str
        """
        return self.send_cmd('?MODE')

    @property
    def status(self):
        """
        Return axis status word 32-bits
        IcePAP user manual pag. 128
        :return: int
        """
        return int(self.send_cmd('?STATUS')[0], 16)

    @property
    def state(self):
        """
        Read the axis status and return a util.State object
        :return: State
        """
        return State(self.status)

    @property
    def vstatus(self):
        """
        Return the axis status as multi-line verbose answer.
        IcePAP user manual pag. 146
        :return: [str]
        """
        return self.send_cmd('?VSTATUS')

    @property
    def stopcode(self):
        """
        Return axis stop code word 16-bits
        IcePAP user manual pag. 130
        :return: int
        """
        return int(self.send_cmd('?STOPCODE')[0], 16)

    @property
    def vstopcode(self):
        """
        Return the message corresponding to the last motion's stop code
        IcePAP user manual pag. 147
        :return: str
        """
        return ' '.join(self.send_cmd('?VSTOPCODE'))

    @property
    def alarm(self):
        """
        Get if the axis is in alarm condition.
        IcePAP user manual pag. 50
        :return: [bool, str]
        """
        ans = self.send_cmd('?ALARM')
        if len(ans) == 1:
            result = (False, '')
        else:
            result = (True, ' '.join(ans))
        return result

    @property
    def warning(self):
        """
        Return a list of string describing warning conditions.
        IcePAP user manual pag. 150
        :return: [str]
        """
        return self.send_cmd('?WARNING')

    @property
    def wtemp(self):
        """
        Get the set temperature warning value
        IcePAP user manual pag. 151
        :return: float
        """
        return float(self.send_cmd('?WTEMP')[0])

    @wtemp.setter
    def wtemp(self, value):
        """
        Set the temperature warning value
        IcePAP user manual pag. 151
        :param value: float
        :return: None
        """
        cmd = 'WTEMP {0}'.format(value)
        self.send_cmd(cmd)

    @property
    def config(self):
        """
        Get the identifier of the last valid configuration. To change the
        configuration use set_config method.
        IcePAP user manual pag. 59
        :return: str
        """
        return self.send_cmd('?CONFIG')[0]

    @property
    def cswitch(self):
        """
        Get the limit switches configuration.
        IcePAP user manual pag. 60
        :return: str
        """
        return self.send_cmd('?CSWITCH')[0]

    @cswitch.setter
    def cswitch(self, value):
        """
        Set the limit switches configuration.
        IcePAP user manual pag. 60
        :param value: str [Normal, Smart, Sticky]
        :return: None
        """
        cmd = 'CSWITCH {0}'.format(value)
        self.send_cmd(cmd)

    @property
    def ver(self):
        """
        Get the version of the all driver modules: Driver, DSP, FPGA, PCB, IO,
        IcePAP user manual pag. 144

        :return: dict{module: (ver, date)}
        """
        ans = self.send_cmd('?VER INFO')
        result = {}
        for line in ans:
            if 'SYSTEM' in line or 'CONTROLLER' in line:
                continue
            v = line.split(':', 2)
            module = v[0].strip()
            value = float(v[1].strip())
            when = ''
            if len(v) > 2:
                when = v[2].strip()
            result[module] = (value, when)
        return result

    @property
    def name(self):
        """
        Get the axis name.
        Icepap user manual pag. 95

        :return: str
        """
        return self.send_cmd('?NAME')[0]

    @name.setter
    def name(self, value):
        """
        Set the axis name. It must lower than 20 characters
        Icepap user manual pag. 95

        :param value: str
        :return: None
        """

        if len(value) >= 20:
            raise ValueError('Name too long, max size 20 characters')
        cmd = 'NAME {0}'.format(value)
        self.send_cmd(cmd)

    @property
    def id(self):
        """
        Get hardware ID and the serial number
        Icepap user manual pag. 80

        :return: (str HW ID, str SN)
        """
        hw_id = self.send_cmd('?ID HW')[0]
        sn_id = self.send_cmd('?ID SN')[0]
        return hw_id, sn_id

    @property
    def post(self):
        """
        Get the result of the power-on self test. Zero means there were not
        errors.
        IcePAP user manual pag. 110

        :return: int
        """
        return int(self.send_cmd('?POST')[0])

    @property
    def power(self):
        """
        Get if the axis is ON
        IcePAP user manual pag. 111

        :return: bool
        """
        return self.send_cmd('?POWER')[0] == 'ON'

    @power.setter
    def power(self, value):
        """
        Set the power of the axis.
        IcePAP user manual pag. 111

        :param value: bool
        :return: None
        """
        cmd = 'POWER {0}'.format(['OFF', 'ON'][value])
        self.send_cmd(cmd)

    @property
    def auxps(self):
        """
        Get if the auxiliary power supply is on
        IcePAP user manual pag. 52
        :return: bool
        """
        return self.send_cmd('?AUXPS')[0] == 'ON'

    @auxps.setter
    def auxps(self, value):
        """
        Set the auxiliary power supply of the axis.
        Icepap user manual pag. 52

        :param value: bool
        :return: None
        """
        cmd = 'AUXPS {0}'.format(['OFF', 'ON'][value])
        self.send_cmd(cmd)

    @property
    def meas_vcc(self):
        """
        Measured value of the main power supply.
        IcePAP user manual pag. 89
        :return: float
        """
        return self.meas('VCC')

    @property
    def meas_vm(self):
        """
        Measured value of the motor voltage.
        IcePAP user manual pag. 89
        :return: float
        """
        return self.meas('VM')

    @property
    def meas_i(self):
        """
        Measured value of the motor current.
        IcePAP user manual pag. 89
        :return: float
        """
        return self.meas('I')

    @property
    def meas_ia(self):
        """
        Measured value of the phase a current.
        IcePAP user manual pag. 89
        :return: float
        """
        return self.meas('IA')

    @property
    def meas_ib(self):
        """
        Measured value of the phase b current.
        IcePAP user manual pag. 89
        :return: float
        """
        return self.meas('IB')

    @property
    def meas_ic(self):
        """
        Measured value of the phase c current.
        IcePAP user manual pag. 89
        :return: float
        """
        return self.meas('IC')

    @property
    def meas_r(self):
        """
        Measured value of the motor resistance.
        IcePAP user manual pag. 89
        :return: float
        """
        return self.meas('R')

    @property
    def meas_ra(self):
        """
        Measured value of the phase a resistance.
        IcePAP user manual pag. 89
        :return: float
        """
        return self.meas('RA')

    @property
    def meas_rb(self):
        """
        Measured value of the phase b resistance.
        IcePAP user manual pag. 89
        :return: float
        """
        return self.meas('RB')

    @property
    def meas_rc(self):
        """
        Measured value of the phase c resistance.
        IcePAP user manual pag. 89
        :return: float
        """
        return self.meas('RC')

    @property
    def meas_t(self):
        """
        Measured value of the board temperature.
        IcePAP user manual pag. 89
        :return: float
        """
        return self.meas('T')

    @property
    def meas_rt(self):
        """
        Measured value of the power supply temperature.
        IcePAP user manual pag. 89
        :return: float
        """
        return self.meas('RT')

    @property
    def pos(self):
        """
        Read the axis nominal position pointer
        IcePAP user manual pag. 108
        :return: long
        """
        return self.get_pos('AXIS')

    @pos.setter
    def pos(self, value):
        """
        Set the axis nominal position value
        IcePAP user manual pag. 108

        :param value: long
        :return: None
        """
        self.set_pos('AXIS', value)

    @property
    def pos_shftenc(self):
        """
        Read the shftenc register.
        IcePAP user manual pag. 108

        :return: long
        """
        return self.get_pos('SHFTENC')

    @pos_shftenc.setter
    def pos_shftenc(self, value):
        """
        Set the shftenc register
        IcePAP user manual pag. 108

        :param value: long
        :return: None
        """
        self.set_pos('SFHTENC', value)

    @property
    def pos_tgtenc(self):
        """
        Read the tgtenc register.
        IcePAP user manual pag. 108

        :return: long
        """
        return self.get_pos('TGTENC')

    @pos_tgtenc.setter
    def pos_tgtenc(self, value):
        """
        Set the tgtenc register
        IcePAP user manual pag. 108

        :param value: long
        :return: None
        """
        self.set_pos('TGTENC', value)

    @property
    def pos_ctrlenc(self):
        """
        Read the ctrlenc register.
        IcePAP user manual pag. 108

        :return: long
        """
        return self.get_pos('CTRLENC')

    @pos_ctrlenc.setter
    def pos_ctrlenc(self, value):
        """
        Set the ctrlenc register
        IcePAP user manual pag. 108

        :param value: long
        :return: None
        """
        self.set_pos('CTRLENC', value)

    @property
    def pos_encin(self):
        """
        Read the encin register.
        IcePAP user manual pag. 108

        :return: long
        """
        return self.get_pos('ENCIN')

    @pos_encin.setter
    def pos_encin(self, value):
        """
        Set the encin register
        IcePAP user manual pag. 108

        :param value: long
        :return: None
        """
        self.set_pos('ENCIN', value)

    @property
    def pos_inpos(self):
        """
        Read the inpos register.
        IcePAP user manual pag. 108

        :return: long
        """
        return self.get_pos('INPOS')

    @pos_inpos.setter
    def pos_inpos(self, value):
        """
        Set the inpos register
        IcePAP user manual pag. 108

        :param value: long
        :return: None
        """
        self.set_pos('INPOS', value)

    @property
    def pos_absenc(self):
        """
        Read the absenc register.
        IcePAP user manual pag. 108

        :return: long
        """
        return self.get_pos('ABSENC')

    @pos_absenc.setter
    def pos_absenc(self, value):
        """
        Set the absenc register
        IcePAP user manual pag. 108

        :param value: long
        :return: None
        """
        self.set_pos('ABSENC', value)

    @property
    def pos_motor(self):
        """
        Read the motor register.
        IcePAP user manual pag. 108

        :return: long
        """
        return self.get_pos('MOTOR')

    @pos_motor.setter
    def pos_motor(self, value):
        """
        Set the motor register
        IcePAP user manual pag. 108

        :param value: long
        :return: None
        """
        self.set_pos('MOTOR', value)

    @property
    def enc(self):
        """
        Read the axis nominal position pointer
        IcePAP user manual pag. 108
        :return: long
        """
        return self.get_enc('AXIS')

    @enc.setter
    def enc(self, value):
        """
        Set the axis nominal position value
        IcePAP user manual pag. 108

        :param value: long
        :return: None
        """
        self.set_enc('AXIS', value)

    @property
    def enc_shftenc(self):
        """
        Read the shftenc register.
        IcePAP user manual pag. 108

        :return: long
        """
        return self.get_enc('SHFTENC')

    @enc_shftenc.setter
    def enc_shftenc(self, value):
        """
        Set the shftenc register
        IcePAP user manual pag. 108

        :param value: long
        :return: None
        """
        self.set_enc('SFHTENC', value)

    @property
    def enc_tgtenc(self):
        """
        Read the tgtenc register.
        IcePAP user manual pag. 108

        :return: long
        """
        return self.get_enc('TGTENC')

    @enc_tgtenc.setter
    def enc_tgtenc(self, value):
        """
        Set the tgtenc register
        IcePAP user manual pag. 108

        :param value: long
        :return: None
        """
        self.set_enc('TGTENC', value)

    @property
    def enc_ctrlenc(self):
        """
        Read the ctrlenc register.
        IcePAP user manual pag. 108

        :return: long
        """
        return self.get_enc('CTRLENC')

    @enc_ctrlenc.setter
    def enc_ctrlenc(self, value):
        """
        Set the ctrlenc register
        IcePAP user manual pag. 108

        :param value: long
        :return: None
        """
        self.set_enc('CTRLENC', value)

    @property
    def enc_encin(self):
        """
        Read the encin register.
        IcePAP user manual pag. 108

        :return: long
        """
        return self.get_enc('ENCIN')

    @enc_encin.setter
    def enc_encin(self, value):
        """
        Set the encin register
        IcePAP user manual pag. 108

        :param value: long
        :return: None
        """
        self.set_enc('ENCIN', value)

    @property
    def enc_inpos(self):
        """
        Read the inpos register.
        IcePAP user manual pag. 108

        :return: long
        """
        return self.get_enc('INPOS')

    @enc_inpos.setter
    def enc_inpos(self, value):
        """
        Set the inpos register
        IcePAP user manual pag. 108

        :param value: long
        :return: None
        """
        self.set_enc('INPOS', value)

    @property
    def enc_absenc(self):
        """
        Read the absenc register.
        IcePAP user manual pag. 108

        :return: long
        """
        return self.get_enc('ABSENC')

    @enc_absenc.setter
    def enc_absenc(self, value):
        """
        Set the absenc register
        IcePAP user manual pag. 108

        :param value: long
        :return: None
        """
        self.set_enc('ABSENC', value)

    @property
    def enc_motor(self):
        """
        Read the motor register.
        IcePAP user manual pag. 108

        :return: long
        """
        return self.get_enc('MOTOR')

    @enc_motor.setter
    def enc_motor(self, value):
        """
        Set the motor register
        IcePAP user manual pag. 108

        :param value: long
        :return: None
        """
        self.set_enc('MOTOR', value)

    @property
    def velocity(self):
        """
        Read the nominal velocity. See get_velocity method

        :return: float
        """
        return self.get_velocity()

    @velocity.setter
    def velocity(self, value):
        """
        Set the nominal velocity. See get_velocity method

        :param value: float
        :return: None
        """
        self.set_velocity(value)

    @property
    def velocity_min(self):
        """
        Read the minimum velocity. See get_velocity method

        :return: float
        """
        return self.get_velocity(vtype='MIN')

    @property
    def velocity_max(self):
        """
        Read the maximum velocity. See get_velocity method

        :return: float
        """
        return self.get_velocity(vtype='MAX')

    @property
    def velocity_default(self):
        """
        Read the default velocity. See get_velocity method

        :return: float
        """
        return self.get_velocity(vtype='DEFAULT')

    @property
    def velocity_current(self):
        """
        Read the default velocity. See get_velocity method

        :return: float
        """
        return self.get_velocity(vtype='CURRENT')

    @property
    def acctime(self):
        """
        Get the acceleration time. See get_acceleration method.

        :return: float
        """
        return self.get_acceleration()

    @acctime.setter
    def acctime(self, value):
        """
        Set the acceleration time. See set_acceleration method.

        :param value: float
        :return: None
        """
        self.set_acceleration(value)

    @property
    def acctime_step(self):
        """
        Get the acceleration in steps distances. See get_acceleration method.
        :return: float
        """
        return self.get_acceleration(atype='STEPS')

    @property
    def acctime_default(self):
        """
        Get the default acceleration time. See get_acceleration method.
        :return: float
        """
        return self.get_acceleration(atype='DEFAULT')

    @property
    def pcloop(self):
        """
        Read if the position close loop is enabled.
        IcePAP user manual pag. 105
        :return: bool
        """
        return self.send_cmd('?PCLOOP')[0] == 'ON'

    @pcloop.setter
    def pcloop(self, value):
        """
        Activate/Deactivate the position close loop
        IcePAP user manual pag. 105
        :param value: bool
        :return: None
        """
        cmd = 'PCLOOP {0}'.format(['OFF', 'ON'][value])
        self.send_cmd(cmd)

    @property
    def jog_velocity(self):
        """
        Get the current jog velocity
        :return: float
        """
        return float(self.send_cmd('?JOG')[0])

    @property
    def indexer(self):
        """
        Get the indexer signal source used for the axis indexer.
        IcePAP user manual pag. 81
        :return: str
        """
        return self.send_cmd('?INDEXER')[0]

    @indexer.setter
    def indexer(self, value):
        """
        Set the indexer signal source.
        IcePAP user manual pag. 81
        :param value: str
        :return: None
        """
        cmd = 'INDEXER {0}'.format(value)
        self.send_cmd(cmd)

    @property
    def parpos(self):
        """
        Get the position on parametric units
        IcePAP user manual pag. 103
        :return: float
        """
        return float(self.send_cmd('?PARPOS')[0])

    @property
    def parvel(self):
        """
        Get the parametric axis velocity
        IcePAP user manual pag. 104
        :return: float
        """
        return float(self.send_cmd('?PARVEL')[0])

    @parvel.setter
    def parvel(self, value):
        """
        Set the parametric axis velocity
        IcePAP user manual pag. 104
        :param value: float
        :return: None
        """
        # NOTE: SOMETIMES PARVEL 10 RETURNS EXCEPTION:
        # xx:PARVEL ERROR Out of range parameter(s)
        # AND IS AVOIDED BY SETTING IT FIRST TO 0 !!!
        values = [0, value]
        for v in values:
            cmd = 'PARVEL {0}'.format(v)
            self.send_cmd(cmd)

    @property
    def paracct(self):
        """
        Get the parametric acceleration time.
        IcePAP user manual pag. 99
        :return: float
        """
        return float(self.send_cmd('?PARACCT')[0])

    @paracct.setter
    def paracct(self, value):
        """
        Set the parametric acceleration time.
        IcePAP user manual pag. 99
        :param value: float
        :return: None
        """
        cmd = 'PARACCT {0}'.format(value)
        self.send_cmd(cmd)

    @property
    def homestat(self):
        """
        Return the homing procedure status.
        IcePAP user manual pag. 79
        :return: [str(state), int(direction)]
        """
        status, direction = self.send_cmd('?HOMESTAT')
        return status, int(direction)

    @property
    def ecam(self):
        """
        Get the electronic cam mode.
        IcePAP user manual pag. 64
        :return: [str] (State, Signal Type, Current Level)
        """
        return self.send_cmd('?ECAM')

    @ecam.setter
    def ecam(self, output):
        """
        Set the electronic cam output: OFF, PULSE, LOW, HIGH.
        IcePAP user manual pag. 64
        :param output: str
        :return: None
        """
        cmd = 'ECAM {0}'.format(output)
        self.send_cmd(cmd)

    @property
    def infoa(self):
        """
        Get the InfoA configuration
        Icepap user manual pag.82
        :return: (str, str) [Signal, Polarity]
        """
        return self.send_cmd('?INFOA')

    @infoa.setter
    def infoa(self, cfg):
        """
        Set the InfoA configuration.
        :param cfg: (str, str) [Signal, Polarity]
        :return: None
        """
        cmd = 'INFOA {0} {1}'.format(*cfg)
        self.send_cmd(cmd)

    @property
    def infob(self):
        """
        Get the InfoB configuration
        Icepap user manual pag.82
        :return: (str, str) [Signal, Polarity]
        """
        return self.send_cmd('?INFOB')

    @infob.setter
    def infob(self, cfg):
        """
        Set the InfoB configuration.
        :param cfg: (str, str) [Signal, Polarity]
        :return: None
        """
        cmd = 'INFOB {0} {1}'.format(*cfg)
        self.send_cmd(cmd)

    @property
    def infoc(self):
        """
        Get the InfoC configuration
        Icepap user manual pag.82
        :return: (str, str) [Signal, Polarity]
        """
        return self.send_cmd('?INFOC')

    @infoc.setter
    def infoc(self, cfg):
        """
        Set the InfoC configuration.
        :param cfg: (str, str) [Signal, Polarity]
        :return: None
        """
        cmd = 'INFOC {0} {1}'.format(*cfg)
        self.send_cmd(cmd)

    @property
    def outpos(self):
        """
        Get the OutPos configuration
        Icepap user manual pag.98
        :return: (str, str) [Signal, Polarity]
        """
        return self.send_cmd('?OUTPOS')

    @outpos.setter
    def outpos(self, cfg):
        """
        Set the OutPos configuration.
        :param cfg: (str, str) [Signal, Polarity]
        :return: None
        """
        cmd = 'OUTPOS {0} {1}'.format(*cfg)
        self.send_cmd(cmd)

    @property
    def outpaux(self):
        """
        Get the OutPAux configuration
        Icepap user manual pag.97
        :return: (str, str) [Signal, Polarity]
        """
        return self.send_cmd('?OUTPAUX')

    @outpaux.setter
    def outpaux(self, cfg):
        """
        Set the OutPAux configuration.
        :param cfg: (str, str) [Signal, Polarity]
        :return: None
        """
        cmd = 'OUTPAUX {0} {1}'.format(*cfg)
        self.send_cmd(cmd)

    @property
    def syncpos(self):
        """
        Get the SyncPos configuration
        Icepap user manual pag.134
        :return: (str, str) [Signal, Polarity]
        """
        return self.send_cmd('?SYNCPOS')

    @syncpos.setter
    def syncpos(self, cfg):
        """
        Set the SyncPos configuration.
        :param cfg: (str, str) [Signal, Polarity]
        :return: None
        """
        cmd = 'SYNCPOS {0} {1}'.format(*cfg)
        self.send_cmd(cmd)

    @property
    def syncaux(self):
        """
        Get the SyncAux configuration
        Icepap user manual pag.82
        :return: (str, str) [Signal, Polarity]
        """
        return self.send_cmd('?SYNCAUX')

    @syncaux.setter
    def syncaux(self, cfg):
        """
        Set the SyncAux configuration.
        :param cfg: (str, str) [Signal, Polarity]
        :return: None
        """
        cmd = 'SYNCAUX {0} {1}'.format(*cfg)
        self.send_cmd(cmd)

# ------------------------------------------------------------------------
#                       Commands
# ------------------------------------------------------------------------

    def blink(self, secs):
        cmd = "BLINK %d" % secs
        self.send_cmd(cmd)

    def send_cmd(self, cmd):
        """
        Wrapper to add the axis number
        :param cmd: Command without axis number
        :return: [str]
        """
        cmd = '{0}:{1}'.format(self._str_id, cmd)
        return self._ctrl.send_cmd(cmd)

    def get_cfginfo(self, parameter=''):
        """
        Get the configuration type for one or all parameters
        :param parameter: str (optional)
        :return: [str]
        """
        cmd = '?CFGINFO {0}'.format(parameter)
        return self.send_cmd(cmd)

    def set_config(self, config=''):
        """
        Set configuration.
        IcePAP user manual pag. 59
        :param config: str
        :return: None
        """
        cmd = 'CONFIG {0}'.format(config)
        self.send_cmd(cmd)

    def get_cfg(self, parameter=''):
        """
        Get the current configuration for one or all parameters
        IcePAP user manual pag. 54
        :param parameter: str (optional)
        :return: [str]
        """
        cmd = '?CFG {0}'.format(parameter)
        return self.send_cmd(cmd)

    def set_cfg(self, *args):
        """
        Set the configuration of a parameter or change to Default/Expert
        configuration.
        IcePAP user manual pag. 54

        :param args: List of arguments: (parameter, value) or ('Default')
        :return: None
        """
        cmd = 'CFG {0}'.format(' '.join(args))
        self.send_cmd(cmd)

    def meas(self, parameter):
        """
        Return a measured value for the parameter.
        IcePAP user manual pag. 89

        :param parameter: str
        :return: float
        """
        cmd = '?MEAS {0}'.format(parameter)
        return float(self.send_cmd(cmd)[0])

    def get_pos(self, register):
        """
        Read the position register in axis units
        IcePAP user manual pag. 108

        :param register: str
        :return: long
        """
        cmd = '?POS {0}'.format(register)
        return long(self.send_cmd(cmd)[0])

    def set_pos(self, register, value):
        """
        Set the position register in axis units
        IcePAP user manual pag. 108

        :param register: str
        :param value: long
        :return: None
        """
        cmd = 'POS {0} {1}'.format(register, long(value))
        self.send_cmd(cmd)

    def get_enc(self, register):
        """
        Read the position register in encoder step
        IcePAP user manual pag. 68
        :param register: str
        :return: long
        """
        cmd = '?ENC {0}'.format(register)
        return long(self.send_cmd(cmd)[0])

    def set_enc(self, register, value):
        """
        Set the position register in encoder step
        IcePAP user manual pag. 68

        :param register: str
        :param value: long
        :return: None
        """
        cmd = 'ENC {0} {1}'.format(register, long(value))
        self.send_cmd(cmd)

    def get_velocity(self, vtype='NOMINAL'):
        """
        Get the velocity.
        IcePAP user manual pag. 143

        :param vtype: str
        :return: float [steps per second]
        """
        cmd = '?VELOCITY {0}'.format(vtype)
        return float(self.send_cmd(cmd)[0])

    def set_velocity(self, value):
        """
        Set the velocity.
        IcePAP user manual pag. 143

        :param value: float
        :return: float [steps per second]
        """
        cmd = 'VELOCITY {0}'.format(value)
        self.send_cmd(cmd)

    def get_acceleration(self, atype='NOMINAL'):
        """
        Read the acceleration time
        IcePAP user manual pag. 48
        :return: float [seconds]
        """
        cmd = '?ACCTIME {0}'.format(atype)
        return float(self.send_cmd(cmd)[0])

    def set_acceleration(self, value):
        """
        Set the acceleration time
        IcePAP user manual pag. 48

        :param value: float
        :return: None
        """
        cmd = 'ACCTIME {0}'.format(value)
        self.send_cmd(cmd)

    def get_home_position(self, register='AXIS'):
        """
        Return the value latched on the position register.
        IcePAP user manual pag. 78
        :param register: str
        :return: long
        """
        cmd = '?HOMEPOS {0}'.format(register)
        return long(self.send_cmd(cmd[0]))

    def get_home_encoder(self, register='AXIS'):
        """
        Return the value latched on encoder register.
        IcePAP user manual pag. 77
        :param register: str
        :return: long
        """
        cmd = '?HOMEENC {0}'.format(register)
        return long(self.send_cmd(cmd[0]))

    def move(self, position):
        """
        Start absolute movement.
        IcePAP user manual pag 92
        :param position: long
        :return: None
        """
        cmd = 'MOVE {0}'.format(long(position))
        self.send_cmd(cmd)

    def umove(self, position):
        """
        Start absolute updated movement.
        IcePAP user manual pag 140
        :param position: long
        :return: None
        """
        cmd = 'UMOVE {0}'.format(long(position))
        self.send_cmd(cmd)

    def rmove(self, position):
        """
        Start absolute relative movement.
        IcePAP user manual pag 140
        :param position: long
        :return: None
        """
        cmd = 'RMOVE {0}'.format(long(position))
        self.send_cmd(cmd)

    def esync(self):
        """
        Synchronize internal position registers
        :return: None
        """

        self.send_cmd('ESYNC')

    def ctrlrst(self):
        """
        Reset control encoder value
        :return: None
        """
        self.send_cmd('CTRLRST')

    def jog(self, veloctiy):
        """
        Start the jog mode at the given velocity.
        IcePAP user manual pag. 85

        :param veloctiy: float
        :return: None
        """
        cmd = 'JOG {0}'.format(veloctiy)
        self.send_cmd(cmd)

    def stop(self):
        """
        Stop the current movement with a normal deceleration ramp
        IcePAP user manual pag. 129

        :return: None
        """
        self.send_cmd('STOP')

    def abort(self):
        """
        Abort the current movement.
        IcePAP user manual pag. 46

        :return: None
        """
        self.send_cmd('ABORT')

    def home(self, mode=1):
        """
        Start home signal search sequence.
        Icepap user manual pag. 76
        :param mode: int [-1, 0, 1]
        :return:
        """
        cmd = 'HOME {0}'.format(mode)
        self.send_cmd(cmd)

    def movel(self, lpos):
        """
        Start postion list movement.
        IcePAP user manual pag. 93
        :param lpos: int
        :return: None
        """
        cmd = 'MOVEL {0}'.format(lpos)
        self.send_cmd(cmd)

    def pmove(self, pos):
        """
        Start parametric movement
        IcePAP user manual pag. 106
        :param pos: float
        :return: None
        """
        cmd = 'PMOVE {0}'.format(pos)
        self.send_cmd(cmd)

    def movep(self, pos):
        """
        Start axis movement to a parameter value
        :param pos: float
        :return: None
        """
        cmd = 'MOVEP {0}'.format(pos)
        self.send_cmd(cmd)

    def cmove(self, pos):
        """
        Start absolute movement in configuration mode.
        IcePAP user manual pag.58
        :param pos: float
        :return: None
        """
        cmd = 'CMOVE {0}'.format(pos)
        self.send_cmd(cmd)

    def cjog(self, vel):
        """
        Set jog velocity in configuration mode
        :param vel:
        :return:
        """
        cmd = 'CJOG {0}'.format(vel)
        self.send_cmd(cmd)

    def track(self, signal, mode='FULL'):
        """
        Start position tracking mode.
        IcePAP user manual pag. 139

        :param signal: str
        :param mode: str
        :return: None
        """
        cmd = 'TRACK {0} {1}'.format(signal, mode)
        self.send_cmd(cmd)

    def ptrack(self, signal, mode='FULL'):
        """
        Start parametric tracking mode.
        IcePAP user manual pag. 114
        :param signal: str
        :param mode: str
        :return: None
        """
        cmd = 'PTRACK {0} {1}'.format(signal, mode)
        self.send_cmd(cmd)

    def set_ecam_table(self, lpos, source='AXIS', dtype='FLOAT'):
        """
        Load the position list to the electronic cam table. The maximum memory
        size of the table is 81908 bytes. After to load the electronic cam
        is ON.
        IcePAP user manual pag. 65

        :param lpos: [float]
        :param source: str
        :param dtype: str
        :return: None
        """
        # Sort the given list of points in ascending order
        # (<list>.sort() slightly more efficient:
        lpos.sort()
        lushorts = self.get_ushort_list(lpos, dtype)
        if len(lushorts) > 40954:
            raise ValueError('There is not enough memory to load the list.')

        cmd = '*ECAMDAT {0} {1}'.format(source, dtype)
        self.send_cmd(cmd)
        self._ctrl._comm.send_binary(lushorts)

    def clear_ecam_table(self):
        """
        Clean the electronic cam table
        Icepap user manual pag. 65
        :return: None
        """
        self.send_cmd('ECAMDAT CLEAR')

    def get_ecam_table(self, dtype='FLOAT'):
        """
        Get the position table loaded on the electronic cam table.
        IcePAP user manual pag. 65
        :param dtype: str
        :return: [float]
        """
        cmd = '?ECAMDAT {0} {1}'
        return self._get_dump_table(cmd, dtype)

    def set_list_table(self, lpos, cyclic=False, dtype='FLOAT'):
        """
        Load a position list table.
        Icepap user manual pag. 87

        :param lpos: [float]
        :param cyclic: bool
        :param dtype: str
        :return: None
        """

        lushorts = self.get_ushort_list(lpos, dtype)
        # if len(lushorts) > 40954:
        #     raise ValueError('There is not enough memory to load the list.')

        cmd = '*LISTDAT {0} {1}'.format(['NOCYCLIC', 'CYCLIC'][cyclic], dtype)
        self.send_cmd(cmd)
        self._ctrl._comm.send_binary(lushorts)

    def clear_list_table(self):
        """
        Clean the position list table
        Icepap user manual pag. 87
        :return: None
        """
        self.send_cmd('LISTDAT CLEAR')

    def get_list_table(self, dtype='FLOAT'):
        """
        Get the position list table.
        IcePAP user manual pag. 87
        :param dtype: str
        :return: [float]
        """
        cmd = '?LISTDAT {0} {1}'
        return self._get_dump_table(cmd, dtype)

    def set_parametric_table(self, lparam, lpos, lslope=None, mode='SPLINE'):
        """
        Method to set the parametric trajectory data.
        IcePAP user manual pag. 100

        :param lparam: [float]
        :param lpos: [float]
        :param lslope: [float]
        :param mode: str [Linear, Spline, Cyclic]'
        :return: None
        """
        data = vdata()
        data.append(lparam, ADDRUNSET, PARAMETER)
        data.append(lpos, self._axis_nr, POSITION)
        if lslope is not None:
            data.append(lslope, self.addr, SLOPE)

        bin_data = data.bin().flatten()
        lushorts = self.get_ushort_list(bin_data, dtype='BYTE')
        cmd = '*PARDAT {0}'.format(mode)
        self.send_cmd(cmd)
        self._ctrl._comm.send_binary(lushorts)

    def clear_parametric_table(self):
        """
        Clean the parametric trajectory table.

        :return: None
        """
        self.send_cmd('PARDAT CLEAR')

    def get_parametric_table(self):
        """
        Get the parametric table
        :return: [[float]] ([parameter], [position], [slope])
        """
        MAX_SUBSET_SIZE = 20
        nr_points = int(self.send_cmd('?PARDAT NPTS')[0])
        if nr_points < MAX_SUBSET_SIZE:
            MAX_SUBSET_SIZE = nr_points

        lparam = []
        lpos = []
        lslope = []
        start_pos = 0
        cmd = '?PARDAT {0} {1}'
        for i in range(nr_points / MAX_SUBSET_SIZE):
            raw_values = self.send_cmd(cmd.format(start_pos, MAX_SUBSET_SIZE))
            start_pos += MAX_SUBSET_SIZE
            for raw_value in raw_values:
                param, pos, slope = raw_value.strip().split()
                lparam.append(param)
                lpos.append(pos)
                lslope.append(slope)
        if (nr_points % MAX_SUBSET_SIZE) > 0:
            last_points = nr_points - start_pos
            raw_values = self.send_cmd(cmd.format(start_pos, last_points))
            for raw_value in raw_values:
                param, pos, slope = raw_value.strip().split()
                lparam.append(param)
                lpos.append(pos)
                lslope.append(slope)

        return lparam, lpos, lslope

    def get_parval(self, parameter):
        """
        Get the motor position for a parameter value.
        :param parameter: float
        :return: float
        """
        cmd = '?PARVAL {0}'.format(parameter)
        return float(self.send_cmd(cmd)[0])

    def print_commands(self):
        """
        Get the allows commands ?HELP
        IcePAP user manual pag. 75
        :return: None
        """
        ans = self.send_cmd('?HELP')
        print('\n'.join(ans))

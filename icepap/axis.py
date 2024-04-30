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

import weakref
import struct
import collections
from .vdatalib import vdata, ADDRUNSET, POSITION, PARAMETER, SLOPE, DWORD, \
    FLOAT
from .utils import State
from .fwversion import FirmwareVersion

__all__ = ['IcePAPAxis']


class IcePAPAxis:
    """
    The IcePAP axis class contains the common IcePAP ASCii API for any
    IcePAP axis. The methods here implemented correspond to those
    at the axis level.
    """
    def __init__(self, ctrl, axis_nr):
        ref = weakref.ref(ctrl)
        self._ctrl = ref()
        self._axis_nr = axis_nr

        # if self._axis_nr != self.addr:
        #     msg = 'Initialization error: axis_nr {0} != adr {1}'.format(
        #         self._axis_nr, self.addr)
        #     raise RuntimeError(msg)

    def __repr__(self):
        return '{}({})'.format(type(self).__name__, self._axis_nr)

    def __str__(self):
        return 'IcePAPAxis {} on {}'.format(self._axis_nr, self._ctrl)

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
    def axis(self):
        """
        Get the axis number (IcePAP user manual pag. 49).
        Local internal address (no communication with the IcePAP)

        :return: int
        """
        return self._axis_nr

    @property
    def addr(self):
        """
        Get the axis number (IcePAP user manual pag. 49).

        :return: int
        """
        return int(self.send_cmd('?ADDR')[0])

    @property
    def active(self):
        """
        Get if the axis is active (IcePAP user manual pag. 47).

        :return: bool
        """
        ans = self.send_cmd('?ACTIVE')[0].upper()
        return ans == 'YES'

    @property
    def mode(self):
        """
        Return the current mode of the axis: CONFIG, OPER, PROG, TEST, FAIL
        (IcePAP user manual pag. 91).

        :return: str
        """
        return self.send_cmd('?MODE')[0]

    @property
    def status(self):
        """
        Return axis status word 32-bits (IcePAP user manual pag. 128).

        :return: int
        """
        return int(self.send_cmd('?STATUS')[0], 16)

    @property
    def state(self):
        """
        Read the axis status and return a util.State object.

        :return: State
        """
        return State(self.status)

    @property
    def state_present(self):
        """
        Check if the present flag is active.

        :return: bool
        """
        return self.state.is_present()

    @property
    def state_alive(self):
        """
        Check if the alive flag is active.

        :return: bool
        """
        return self.state.is_alive()

    @property
    def state_mode_code(self):
        """
        Return the current mode.

        :return: int
        """
        return self.state.get_mode_code()

    @property
    def state_mode_str(self):
        """
        Return the current mode.

        :return: str
        """
        return self.state.get_mode_str()

    @property
    def state_disabled(self):
        """
        Check if the disable flag is active.

        :return: bool
        """
        return self.state.is_disabled()

    @property
    def state_disable_code(self):
        """
        Return the disable code.

        :return: int
        """
        return self.state.get_disable_code()

    @property
    def state_disable_str(self):
        """
        Return the disable string.

        :return: str
        """
        return self.state.get_disable_str()

    @property
    def state_indexer_code(self):
        """
        Return the indexer code.

        :return: int
        """
        return self.state.get_indexer_code()

    @property
    def state_indexer_str(self):
        """
        Return the indexer string.

        :return: str
        """
        return self.state.get_indexer_str()

    @property
    def state_moving(self):
        """
        Check if the moving flag is active.

        :return: bool
        """
        return self.state.is_moving()

    @property
    def state_ready(self):
        """
        Check if the ready flag is active.

        :return: bool
        """
        return self.state.is_ready()

    @property
    def state_settling(self):
        """
        Check if the settling flag is active.

        :return: bool
        """
        return self.state.is_settling()

    @property
    def state_outofwin(self):
        """
        Check if the outofwin flag is active.

        :return: bool
        """
        return self.state.is_outofwin()

    @property
    def state_warning(self):
        """
        Check if the warning flag is active.

        :return: bool
        """
        return self.state.is_warning()

    @property
    def state_stop_code(self):
        """
        Return the stop code.

        :return: int
        """
        return self.state.get_stop_code()

    @property
    def state_stop_str(self):
        """
        Return the stop string.

        :return: str
        """
        return self.state.get_stop_str()

    @property
    def state_limit_positive(self):
        """
        Check if the flag limit_positive is active.

        :return: bool
        """
        return self.state.is_limit_positive()

    @property
    def state_limit_negative(self):
        """
        Check if the flag limit_negative is active.

        :return: bool
        """
        return self.state.is_limit_negative()

    @property
    def state_inhome(self):
        """
        Chekc if the home flag is active.

        :return: bool
        """
        return self.state.is_inhome()

    @property
    def state_5vpower(self):
        """
        Check if the auxiliary power is On.

        :return: bool
        """
        return self.state.is_5vpower()

    @property
    def state_verserr(self):
        """
        Check if the vererr flag is active.

        :return: bool
        """
        return self.state.is_verserr()

    @property
    def state_poweron(self):
        """
        Check if the flag poweron is active.

        :return: bool
        """
        return self.state.is_poweron()

    @property
    def state_info_code(self):
        """
        Return the info code.

        :return: int
        """
        return self.state.get_info_code()

    @property
    def vstatus(self):
        """
        Return the axis status as multi-line verbose answer (IcePAP user
        manual pag. 146).

        :return: str
        """
        return '\n'.join(self.send_cmd('?VSTATUS'))

    @property
    def stopcode(self):
        """
        Return axis stop code word 16-bits (IcePAP user manual pag. 130).

        :return: int
        """
        return int(self.send_cmd('?STOPCODE')[0], 16)

    @property
    def vstopcode(self):
        """
        Return the message corresponding to the last motion's stop code
        (IcePAP user manual pag. 147).

        :return: str
        """
        return ' '.join(self.send_cmd('?VSTOPCODE'))

    @property
    def alarm(self):
        """
        Get if the axis is in alarm condition (IcePAP user manual pag. 50).

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
        Return a list of string describing warning conditions (IcePAP user
        manual pag. 150).

        :return: [str]
        """
        return self.send_cmd('?WARNING')

    @property
    def wtemp(self):
        """
        Get the set temperature warning value (IcePAP user manual pag. 151).

        :return: float
        """
        return float(self.send_cmd('?WTEMP')[0])

    @wtemp.setter
    def wtemp(self, value):
        """
        Set the temperature warning value (IcePAP user manual pag. 151).

        :param value: float
        """
        cmd = 'WTEMP {0}'.format(value)
        self.send_cmd(cmd)

    @property
    def config(self):
        """
        Get the identifier of the last valid configuration. To change the
        configuration use set_config method (IcePAP user manual pag. 59).

        :return: str
        """
        config = self.send_cmd('?CONFIG')
        if config is None:
            config = ""
        else:
            config = config[0]
        return config

    @property
    def cswitch(self):
        """
        Get the limit switches configuration (IcePAP user manual pag. 60).

        :return: str
        """
        return self.send_cmd('?CSWITCH')[0]

    @cswitch.setter
    def cswitch(self, value):
        """
        Set the limit switches configuration (IcePAP user manual pag. 60).

        :param value: str [Normal, Smart, Sticky]
        """
        cmd = 'CSWITCH {0}'.format(value)
        self.send_cmd(cmd)

    @property
    def ver(self):
        """
        Get the version of the all driver modules: Driver, DSP, FPGA, PCB, IO
        (IcePAP user manual pag. 144).

        :return: dict{module: (ver, date)}
        """
        ans = self.send_cmd('?VER INFO')
        return FirmwareVersion(ans, True)

    @property
    def fver(self):
        """
        Get the only driver version 'axis:?VER'
        (IcePAP user manual pag. 144).

        :return: float
        """
        ans = self.send_cmd('?VER')[0]
        return float(ans)

    @property
    def name(self):
        """
        Get the axis name (Icepap user manual pag. 95).

        :return: str
        """
        value = self.send_cmd('?NAME')
        if isinstance(value, list):
            value = ' '.join(value)
        return value

    @name.setter
    def name(self, value):
        """
        Set the axis name. (Icepap user manual pag. 95).

        :param value: str
        """

        cmd = 'NAME {0}'.format(value)
        self.send_cmd(cmd)

    @property
    def id(self):
        """
        Get hardware ID and the serial number (Icepap user manual pag. 80).
        Ignoring errors from ?ID SN commands, return empty string in that case

        :return: (str HW ID, str SN)
        """
        hw_id = self.send_cmd('?ID HW')[0]
        sn_id = ''
        try:
            sn_ = self.send_cmd("?ID SN")
            if sn_ is not None:
                sn_id = sn_[0]
        except Exception as e:
            self.log.error("Cannot read axis Serial Number %s", str(e).strip())            
    
        return hw_id, sn_id

    @property
    def post(self):
        """
        Get the result of the power-on self test. Zero means there were not
        errors (IcePAP user manual pag. 110).

        :return: int
        """
        return int(self.send_cmd('?POST')[0])

    @property
    def power(self):
        """
        Get if the axis is ON (IcePAP user manual pag. 111).

        :return: bool
        """
        return self.send_cmd('?POWER')[0] == 'ON'

    @power.setter
    def power(self, value):
        """
        Set the power of the axis (IcePAP user manual pag. 111).

        :param value: bool
        """
        cmd = 'POWER {0}'.format(['OFF', 'ON'][value])
        self.send_cmd(cmd)

    @property
    def auxps(self):
        """
        Get if the auxiliary power supply is ON (IcePAP user manual pag. 52).

        :return: bool
        """
        return self.send_cmd('?AUXPS')[0] == 'ON'

    @auxps.setter
    def auxps(self, value):
        """
        Set the auxiliary power supply of the axis (Icepap user manual pag.
        52).

        :param value: bool
        """
        cmd = 'AUXPS {0}'.format(['OFF', 'ON'][value])
        self.send_cmd(cmd)

    @property
    def meas_vcc(self):
        """
        Measured value of the main power supply (IcePAP user manual pag. 89).

        :return: float
        """
        return self.meas('VCC')

    @property
    def meas_vm(self):
        """
        Measured value of the motor voltage (IcePAP user manual pag. 89).

        :return: float
        """
        return self.meas('VM')

    @property
    def meas_i(self):
        """
        Measured value of the motor current (IcePAP user manual pag. 89).

        :return: float
        """
        return self.meas('I')

    @property
    def meas_ia(self):
        """
        Measured value of the phase a current (IcePAP user manual pag. 89).

        :return: float
        """
        return self.meas('IA')

    @property
    def meas_ib(self):
        """
        Measured value of the phase b current (IcePAP user manual pag. 89).

        :return: float
        """
        return self.meas('IB')

    @property
    def meas_ic(self):
        """
        Measured value of the phase c current (IcePAP user manual pag. 89).

        :return: float
        """
        return self.meas('IC')

    @property
    def meas_r(self):
        """
        Measured value of the motor resistance (IcePAP user manual pag. 89).

        :return: float
        """
        return self.meas('R')

    @property
    def meas_ra(self):
        """
        Measured value of the phase a resistance (IcePAP user manual pag. 89).

        :return: float
        """
        return self.meas('RA')

    @property
    def meas_rb(self):
        """
        Measured value of the phase b resistance (IcePAP user manual pag. 89).

        :return: float
        """
        return self.meas('RB')

    @property
    def meas_rc(self):
        """
        Measured value of the phase c resistance (IcePAP user manual pag. 89).

        :return: float
        """
        return self.meas('RC')

    @property
    def meas_t(self):
        """
        Measured value of the board temperature (IcePAP user manual pag. 89).

        :return: float
        """
        return self.meas('T')

    @property
    def meas_rt(self):
        """
        Measured value of the power supply temperature (IcePAP user manual
        pag. 89).

        :return: float
        """
        return self.meas('RT')

    @property
    def pos(self):
        """
        Read the axis nominal position pointer (IcePAP user manual pag. 108).

        :return: int
        """
        return self.get_pos('AXIS')

    @pos.setter
    def pos(self, value):
        """
        Set the axis nominal position value (IcePAP user manual pag. 108).

        :param value: int
        """
        self.set_pos('AXIS', value)

    @property
    def pos_measure(self):
        """
        Read the measure register (IcePAP user manual pag. 108).

        :return: int
        """
        return self.get_pos('MEASURE')

    @pos_measure.setter
    def pos_measure(self, value):
        """
        Set the measure register (IcePAP user manual pag. 108).

        :param value: int
        """
        self.set_pos('MEASURE', value)

    @property
    def pos_shftenc(self):
        """
        Read the shftenc register (IcePAP user manual pag. 108).

        :return: int
        """
        return self.get_pos('SHFTENC')

    @pos_shftenc.setter
    def pos_shftenc(self, value):
        """
        Set the shftenc register (IcePAP user manual pag. 108).

        :param value: int
        """
        self.set_pos('SHFTENC', value)

    @property
    def pos_tgtenc(self):
        """
        Read the tgtenc register (IcePAP user manual pag. 108).

        :return: int
        """
        return self.get_pos('TGTENC')

    @pos_tgtenc.setter
    def pos_tgtenc(self, value):
        """
        Set the tgtenc register (IcePAP user manual pag. 108).

        :param value: int
        """
        self.set_pos('TGTENC', value)

    @property
    def pos_ctrlenc(self):
        """
        Read the ctrlenc register (IcePAP user manual pag. 108).

        :return: int
        """
        return self.get_pos('CTRLENC')

    @pos_ctrlenc.setter
    def pos_ctrlenc(self, value):
        """
        Set the ctrlenc register (IcePAP user manual pag. 108).

        :param value: int
        """
        self.set_pos('CTRLENC', value)

    @property
    def pos_encin(self):
        """
        Read the encin register (IcePAP user manual pag. 108).

        :return: int
        """
        return self.get_pos('ENCIN')

    @pos_encin.setter
    def pos_encin(self, value):
        """
        Set the encin register (IcePAP user manual pag. 108).

        :param value: int
        """
        self.set_pos('ENCIN', value)

    @property
    def pos_inpos(self):
        """
        Read the inpos register (IcePAP user manual pag. 108).

        :return: int
        """
        return self.get_pos('INPOS')

    @pos_inpos.setter
    def pos_inpos(self, value):
        """
        Set the inpos register (IcePAP user manual pag. 108).

        :param value: int
        """
        self.set_pos('INPOS', value)

    @property
    def pos_absenc(self):
        """
        Read the absenc register (IcePAP user manual pag. 108).

        :return: int
        """
        return self.get_pos('ABSENC')

    @pos_absenc.setter
    def pos_absenc(self, value):
        """
        Set the absenc register (IcePAP user manual pag. 108).

        :param value: int
        """
        self.set_pos('ABSENC', value)

    @property
    def pos_motor(self):
        """
        Read the motor register (IcePAP user manual pag. 108).

        :return: int
        """
        return self.get_pos('MOTOR')

    @pos_motor.setter
    def pos_motor(self, value):
        """
        Set the motor register (IcePAP user manual pag. 108).

        :param value: int
        """
        self.set_pos('MOTOR', value)

    @property
    def pos_sync(self):
        """
        Read the sync register (IcePAP user manual pag. 108).

        :return: int
        """
        return self.get_pos('SYNC')

    @pos_sync.setter
    def pos_sync(self, value):
        """
        Set the sync register (IcePAP user manual pag. 108).

        :param value: int
        """
        self.set_pos('SYNC', value)

    @property
    def enc(self):
        """
        Read the axis nominal position pointer (IcePAP user manual pag. 108).

        :return: int
        """
        return self.get_enc('AXIS')

    @enc.setter
    def enc(self, value):
        """
        Set the axis nominal position value (IcePAP user manual pag. 108).

        :param value: int
        """
        self.set_enc('AXIS', value)

    @property
    def enc_measure(self):
        """
        Read the measure register (IcePAP user manual pag. 108).

        :return: int
        """
        return self.get_enc('MEASURE')

    @enc_measure.setter
    def enc_measure(self, value):
        """
        Set the measure register (IcePAP user manual pag. 108).

        :param value: int
        """
        self.set_enc('MEASURE', value)

    @property
    def enc_shftenc(self):
        """
        Read the shftenc register (IcePAP user manual pag. 108).

        :return: int
        """
        return self.get_enc('SHFTENC')

    @enc_shftenc.setter
    def enc_shftenc(self, value):
        """
        Set the shftenc register (IcePAP user manual pag. 108).

        :param value: int
        """
        self.set_enc('SHFTENC', value)

    @property
    def enc_tgtenc(self):
        """
        Read the tgtenc register (IcePAP user manual pag. 108).

        :return: int
        """
        return self.get_enc('TGTENC')

    @enc_tgtenc.setter
    def enc_tgtenc(self, value):
        """
        Set the tgtenc register (IcePAP user manual pag. 108).

        :param value: int
        """
        self.set_enc('TGTENC', value)

    @property
    def enc_ctrlenc(self):
        """
        Read the ctrlenc register (IcePAP user manual pag. 108).

        :return: int
        """
        return self.get_enc('CTRLENC')

    @enc_ctrlenc.setter
    def enc_ctrlenc(self, value):
        """
        Set the ctrlenc register (IcePAP user manual pag. 108).

        :param value: int
        """
        self.set_enc('CTRLENC', value)

    @property
    def enc_encin(self):
        """
        Read the encin register (IcePAP user manual pag. 108).

        :return: int
        """
        return self.get_enc('ENCIN')

    @enc_encin.setter
    def enc_encin(self, value):
        """
        Set the encin register (IcePAP user manual pag. 108).

        :param value: int
        """
        self.set_enc('ENCIN', value)

    @property
    def enc_inpos(self):
        """
        Read the inpos register (IcePAP user manual pag. 108).

        :return: int
        """
        return self.get_enc('INPOS')

    @enc_inpos.setter
    def enc_inpos(self, value):
        """
        Set the inpos register (IcePAP user manual pag. 108).

        :param value: int
        """
        self.set_enc('INPOS', value)

    @property
    def enc_absenc(self):
        """
        Read the absenc register (IcePAP user manual pag. 108).

        :return: int
        """
        return self.get_enc('ABSENC')

    @enc_absenc.setter
    def enc_absenc(self, value):
        """
        Set the absenc register (IcePAP user manual pag. 108).

        :param value: int
        """
        self.set_enc('ABSENC', value)

    @property
    def enc_motor(self):
        """
        Read the motor register (IcePAP user manual pag. 108).

        :return: int
        """
        return self.get_enc('MOTOR')

    @enc_motor.setter
    def enc_motor(self, value):
        """
        Set the motor register (IcePAP user manual pag. 108).

        :param value: int
        """
        self.set_enc('MOTOR', value)

    @property
    def enc_sync(self):
        """
        Read the sync register (IcePAP user manual pag. 108).

        :return: int
        """
        return self.get_enc('SYNC')

    @enc_sync.setter
    def enc_sync(self, value):
        """
        Set the sync register (IcePAP user manual pag. 108).

        :param value: int
        """
        self.set_enc('SYNC', value)

    @property
    def velocity(self):
        """
        Read the nominal velocity (see get_velocity method).

        :return: float
        """
        return self.get_velocity()

    @velocity.setter
    def velocity(self, value):
        """
        Set the nominal velocity (see get_velocity method).

        :param value: float
        """
        self.set_velocity(value)

    @property
    def velocity_min(self):
        """
        Read the minimum velocity (see get_velocity method).

        :return: float
        """
        return self.get_velocity(vtype='MIN')

    @property
    def velocity_max(self):
        """
        Read the maximum velocity (see get_velocity method).

        :return: float
        """
        return self.get_velocity(vtype='MAX')

    @property
    def velocity_default(self):
        """
        Read the default velocity (see get_velocity method).

        :return: float
        """
        return self.get_velocity(vtype='DEFAULT')

    @property
    def velocity_current(self):
        """
        Read the default velocity (see get_velocity method).

        :return: float
        """
        return self.get_velocity(vtype='CURRENT')

    @property
    def acctime(self):
        """
        Get the acceleration time (see get_acceleration method).

        :return: float
        """
        return self.get_acceleration()

    @acctime.setter
    def acctime(self, value):
        """
        Set the acceleration time (see set_acceleration method).

        :param value: float
        """
        self.set_acceleration(value)

    @property
    def acctime_steps(self):
        """
        Get the acceleration in steps distances (see get_acceleration method).

        :return: float
        """
        return self.get_acceleration(atype='STEPS')

    @property
    def acctime_default(self):
        """
        Get the default acceleration time (see get_acceleration method).

        :return: float
        """
        return self.get_acceleration(atype='DEFAULT')

    @property
    def pcloop(self):
        """
        Read if the position close loop is enabled (IcePAP user manual
        pag. 105).

        :return: bool
        """
        return self.send_cmd('?PCLOOP')[0] == 'ON'

    @pcloop.setter
    def pcloop(self, value):
        """
        Activate/Deactivate the position close loop (IcePAP user manual
        pag. 105)

        :param value: bool
        """
        cmd = 'PCLOOP {0}'.format(['OFF', 'ON'][value])
        self.send_cmd(cmd)

    @property
    def jog_velocity(self):
        """
        Get the current jog velocity.

        :return: float
        """
        return float(self.send_cmd('?JOG')[0])

    @property
    def indexer(self):
        """
        Get the indexer signal source used for the axis indexer (IcePAP user
        manual pag. 81).

        :return: str
        """
        return self.send_cmd('?INDEXER')[0]

    @indexer.setter
    def indexer(self, value):
        """
        Set the indexer signal source (IcePAP user manual pag. 81).

        :param value: str
        """
        cmd = 'INDEXER {0}'.format(value)
        self.send_cmd(cmd)

    @property
    def parpos(self):
        """
        Get the position on parametric units (IcePAP user manual pag. 103).

        :return: float
        """
        return float(self.send_cmd('?PARPOS')[0])

    @property
    def parvel(self):
        """
        Get the parametric axis velocity (IcePAP user manual pag. 104).

        :return: float
        """
        return float(self.send_cmd('?PARVEL')[0])

    @parvel.setter
    def parvel(self, value):
        """
        Set the parametric axis velocity (IcePAP user manual pag. 104).

        :param value: float
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
        Get the parametric acceleration time (IcePAP user manual pag. 99).

        :return: float
        """
        return float(self.send_cmd('?PARACCT')[0])

    @paracct.setter
    def paracct(self, value):
        """
        Set the parametric acceleration time (IcePAP user manual pag. 99).

        :param value: float
        """
        cmd = 'PARACCT {0}'.format(value)
        self.send_cmd(cmd)

    @property
    def homestat(self):
        """
        Return the homing procedure status (IcePAP user manual pag. 79).

        :return: [str(state), int(direction)]
        """
        status, direction = self.send_cmd('?HOMESTAT')
        return status, int(direction)

    @property
    def srchstat(self):
        """
        Return the homing procedure status.
        (IcePAP user manual page 132, v1.0c).

        :return: [str(state), int(direction)]
        """
        status, direction = self.send_cmd('?SRCHSTAT')
        return status, int(direction)

    @property
    def ecam(self):
        """
        Get the electronic cam mode (IcePAP user manual pag. 64).

        :return: str
        """
        return ' '.join(self.send_cmd('?ECAM'))

    @ecam.setter
    def ecam(self, output):
        """
        Set the electronic cam output: OFF, PULSE, LOW, HIGH (IcePAP user
        manual pag. 64).

        :param output: str
        """
        cmd = 'ECAM {0}'.format(output)
        self.send_cmd(cmd)

    @property
    def infoa(self):
        """
        Get the InfoA configuration (Icepap user manual pag. 82).

        :return: (str, str) [Signal, Polarity]
        """
        return self.send_cmd('?INFOA')

    @infoa.setter
    def infoa(self, cfg):
        """
        Set the InfoA configuration.

        :param cfg: (str, str) [Signal, Polarity]
        """
        cfg = ' '.join(cfg)
        cmd = 'INFOA {0}'.format(cfg)
        self.send_cmd(cmd)

    @property
    def infob(self):
        """
        Get the InfoB configuration (Icepap user manual pag. 82).

        :return: (str, str) [Signal, Polarity]
        """
        return self.send_cmd('?INFOB')

    @infob.setter
    def infob(self, cfg):
        """
        Set the InfoB configuration.

        :param cfg: (str, str) [Signal, Polarity]
        """
        cfg = ' '.join(cfg)
        cmd = 'INFOB {0}'.format(cfg)
        self.send_cmd(cmd)

    @property
    def infoc(self):
        """
        Get the InfoC configuration (Icepap user manual pag. 82).

        :return: (str, str) [Signal, Polarity]
        """
        return self.send_cmd('?INFOC')

    @infoc.setter
    def infoc(self, cfg):
        """
        Set the InfoC configuration.

        :param cfg: (str, str) [Signal, Polarity]
        """
        cfg = ' '.join(cfg)
        cmd = 'INFOC {0}'.format(cfg)
        self.send_cmd(cmd)

    @property
    def outpos(self):
        """
        Get the OutPos configuration (Icepap user manual pag. 98)

        :return: (str, str) [Signal, Polarity]
        """
        return self.send_cmd('?OUTPOS')

    @outpos.setter
    def outpos(self, cfg):
        """
        Set the OutPos configuration.

        :param cfg: (str, str) [Signal, Polarity]
        """
        cfg = ' '.join(cfg)
        cmd = 'OUTPOS {0}'.format(cfg)
        self.send_cmd(cmd)

    @property
    def outpaux(self):
        """
        Get the OutPAux configuration (Icepap user manual pag. 97).

        :return: (str, str) [Signal, Polarity]
        """
        return self.send_cmd('?OUTPAUX')

    @outpaux.setter
    def outpaux(self, cfg):
        """
        Set the OutPAux configuration.

        :param cfg: (str, str) [Signal, Polarity]
        """
        cfg = ' '.join(cfg)
        cmd = 'OUTPAUX {0}'.format(cfg)
        self.send_cmd(cmd)

    @property
    def syncpos(self):
        """
        Get the SyncPos configuration (Icepap user manual pag. 134).

        :return: (str, str) [Signal, Polarity]
        """
        return self.send_cmd('?SYNCPOS')

    @syncpos.setter
    def syncpos(self, cfg):
        """
        Set the SyncPos configuration.

        :param cfg: (str, str) [Signal, Polarity]
        """
        cfg = ' '.join(cfg)
        cmd = 'SYNCPOS {0}'.format(cfg)
        self.send_cmd(cmd)

    @property
    def syncaux(self):
        """
        Get the SyncAux configuration (Icepap user manual pag. 82).

        :return: (str, str) [Signal, Polarity]
        """
        return self.send_cmd('?SYNCAUX')

    @syncaux.setter
    def syncaux(self, cfg):
        """
        Set the SyncAux configuration.

        :param cfg: (str, str) [Signal, Polarity]
        """
        cfg = ' '.join(cfg)
        cmd = 'SYNCAUX {0}'.format(cfg)
        self.send_cmd(cmd)

# ------------------------------------------------------------------------
#                       Commands
# ------------------------------------------------------------------------

    def blink(self, secs):
        """
        Blink the driver status led for a given amount of time (Icepap user
        manual pag. 53).

        :param secs: number of second to blink.
        """
        cmd = "BLINK %d" % secs
        self.send_cmd(cmd)

    def send_cmd(self, cmd):
        """
        Wrapper to add the axis number.

        :param cmd: Command without axis number
        :return: [str]
        """
        cmd = '{0}:{1}'.format(self._axis_nr, cmd)
        return self._ctrl.send_cmd(cmd)

    def get_cfginfo(self, parameter=''):
        """
        Get the configuration type for one or all parameters.

        :param parameter: str (optional)
        :return: dict
        """
        cmd = '?CFGINFO {0}'.format(parameter)
        ans = self.send_cmd(cmd)
        cfg = collections.OrderedDict()
        if parameter == '':
            for line in ans:
                key, value = line.split(' ', 1)
                cfg[key] = value
        else:
            key = ans[0]
            value = ' '.join(ans[1:])
            cfg[key] = value
        return cfg

    def set_config(self, config=''):
        """
        Set configuration (IcePAP user manual pag. 59).

        :param config: str
        """
        cmd = 'CONFIG {0}'.format(config)
        self.send_cmd(cmd)

    def get_cfg(self, parameter=''):
        """
        Get the current configuration for one or all parameters (IcePAP user
        manual pag. 54).

        :param parameter: str (optional)
        :return: dict
        """
        cmd = '?CFG {0}'.format(parameter)
        ans = self.send_cmd(cmd)
        cfg = collections.OrderedDict()
        if parameter.lower() in ['', 'default']:
            for line in ans:
                key, value = line.split(' ', 1)
                cfg[key] = value
        else:
            key, value = ans
            cfg[key] = value
        return cfg

    def set_cfg(self, *args):
        """
        Set the configuration of a parameter or change to Default/Expert
        configuration (IcePAP user manual pag. 54).

        set_cfg('Active', 'YES', 'NVOLT', '48',...)

        :param args: str: parameter, value or ('Default')
        """
        cmd = 'CFG {0}'.format(' '.join(args))
        self.send_cmd(cmd)

    def meas(self, parameter):
        """
        Return a measured value for the parameter (IcePAP user manual pag. 89).

        :param parameter: str
        :return: float
        """
        cmd = '?MEAS {0}'.format(parameter)
        return float(self.send_cmd(cmd)[0])

    def get_pos(self, register):
        """
        Read the position register in axis units (IcePAP user manual pag. 108).

        :param register: str
        :return: int
        """
        cmd = '?POS {0}'.format(register)
        return int(self.send_cmd(cmd)[0])

    def set_pos(self, register, value):
        """
        Set the position register in axis units (IcePAP user manual pag. 108).

        :param register: str
        :param value: int
        """
        cmd = 'POS {0} {1}'.format(register, int(value))
        self.send_cmd(cmd)

    def get_enc(self, register):
        """
        Read the position register in encoder step (IcePAP user manual
        pag. 68).

        :param register: str
        :return: int
        """
        cmd = '?ENC {0}'.format(register)
        return int(self.send_cmd(cmd)[0])

    def set_enc(self, register, value):
        """
        Set the position register in encoder step (IcePAP user manual pag. 68).

        :param register: str
        :param value: int
        """
        cmd = 'ENC {0} {1}'.format(register, int(value))
        self.send_cmd(cmd)

    def get_velocity(self, vtype=''):
        """
        Get the velocity (IcePAP user manual pag. 143).

        :param vtype: str
        :return: float [steps per second]
        """
        cmd = '?VELOCITY {0}'.format(vtype)
        return float(self.send_cmd(cmd)[0])

    def set_velocity(self, value):
        """
        Set the velocity (IcePAP user manual pag. 143).

        :param value: float
        :return: float [steps per second]
        """
        cmd = 'VELOCITY {0}'.format(value)
        self.send_cmd(cmd)

    def get_acceleration(self, atype=''):
        """
        Read the acceleration time (IcePAP user manual pag. 48).

        :return: float [seconds]
        """
        cmd = '?ACCTIME {0}'.format(atype)
        return float(self.send_cmd(cmd)[0])

    def set_acceleration(self, value):
        """
        Set the acceleration time (IcePAP user manual pag. 48).

        :param value: float
        """
        cmd = 'ACCTIME {0}'.format(value)
        self.send_cmd(cmd)

    def get_home_position(self, register='AXIS'):
        """
        Return the home value latched on the position register.
        (IcePAP user manual page 83, v1.0c).

        :param register: str
        :return: int
        """
        cmd = '?HOMEPOS {0}'.format(register)
        return int(self.send_cmd(cmd)[0])

    def get_home_encoder(self, register='AXIS'):
        """
        Return the home value latched on encoder register.
        (IcePAP user manual page 82, v1.0c).

        :param register: str
        :return: int
        """
        cmd = '?HOMEENC {0}'.format(register)
        return int(self.send_cmd(cmd)[0])

    def get_srch_position(self, register='AXIS'):
        """
        Return the search value latched on the position register.
        (IcePAP user manual page 131, v1.0c).

        :param register: str
        :return: int
        """
        cmd = '?SRCHPOS {0}'.format(register)
        return int(self.send_cmd(cmd)[0])

    def get_srch_encoder(self, register='AXIS'):
        """
        Return the search value latched on encoder register.
        (IcePAP user manual page 130, v1.0c).

        :param register: str
        :return: int
        """
        cmd = '?SRCHENC {0}'.format(register)
        return int(self.send_cmd(cmd)[0])

    def move(self, position):
        """
        Start absolute movement (IcePAP user manual pag. 92).

        :param position: int
        """
        cmd = 'MOVE {0}'.format(int(position))
        self.send_cmd(cmd)

    def umove(self, position):
        """
        Start absolute updated movement (IcePAP user manual pag. 140).

        :param position: int
        """
        cmd = 'UMOVE {0}'.format(int(position))
        self.send_cmd(cmd)

    def rmove(self, position):
        """
        Start absolute relative movement (IcePAP user manual pag. 140).

        :param position: int
        """
        cmd = 'RMOVE {0}'.format(int(position))
        self.send_cmd(cmd)

    def esync(self):
        """
        Synchronize internal position registers.
        """
        self.send_cmd('ESYNC')

    def ctrlrst(self):
        """
        Reset control encoder value.
        """
        self.send_cmd('CTRLRST')

    def jog(self, veloctiy):
        """
        Start the jog mode at the given velocity (IcePAP user manual pag. 85).

        :param veloctiy: float
        """
        cmd = 'JOG {0}'.format(veloctiy)
        self.send_cmd(cmd)

    def stop(self):
        """
        Stop the current movement with a normal deceleration ramp (IcePAP user
        manual pag. 129).
        """
        self.send_cmd('STOP')

    def abort(self):
        """
        Abort the current movement (IcePAP user manual pag. 46).
        """
        self.send_cmd('ABORT')

    def home(self, mode=1):
        """
        Start home signal search sequence (Icepap user manual pag. 76).

        :param mode: int [-1, 0, 1]
        """
        cmd = 'HOME {0}'.format(mode)
        self.send_cmd(cmd)

    def srch(self, signal, edge_type, direction):
        """
        Start search sequence.
        (IcePAP user manual page 129, v1.0c).

        :param signal: str ['LIM-', 'LIM+', 'HOME', 'ENCAUX', 'INPAUX']
        :param edge_type: str ['POSEDGE', 'NEGEDGE']
        :param direction: int [-1, 1]
        """
        # TODO: Investigate why it does not work with '1' like home command
        cmd = 'SRCH {0} {1} {2:+}'.format(signal, edge_type, direction)
        self.send_cmd(cmd)

    def movel(self, lpos):
        """
        Start postion list movement (IcePAP user manual pag. 93).

        :param lpos: int
        """
        cmd = 'MOVEL {0}'.format(lpos)
        self.send_cmd(cmd)

    def pmove(self, pos):
        """
        Start parametric movement (IcePAP user manual pag. 106).

        :param pos: float
        """
        cmd = 'PMOVE {0}'.format(pos)
        self.send_cmd(cmd)

    def movep(self, pos):
        """
        Start axis movement to a parameter value.

        :param pos: float
        """
        cmd = 'MOVEP {0}'.format(pos)
        self.send_cmd(cmd)

    def cmove(self, pos):
        """
        Start absolute movement in configuration mode (IcePAP user manual
        pag.58).

        :param pos: float
        """
        cmd = 'CMOVE {0}'.format(pos)
        self.send_cmd(cmd)

    def cjog(self, vel):
        """
        Set jog velocity in configuration mode.

        :param vel: float
        """
        cmd = 'CJOG {0}'.format(vel)
        self.send_cmd(cmd)

    def track(self, signal, mode='FULL'):
        """
        Start position tracking mode (IcePAP user manual pag. 139).

        :param signal: str
        :param mode: str
        """
        cmd = 'TRACK {0} {1}'.format(signal, mode)
        self.send_cmd(cmd)

    def ptrack(self, signal, mode='FULL'):
        """
        Start parametric tracking mode (IcePAP user manual pag. 114).

        :param signal: str
        :param mode: str
        """
        cmd = 'PTRACK {0} {1}'.format(signal, mode)
        self.send_cmd(cmd)

    def ltrack(self, signal="", mode='CYCLIC'):
        """
        Start list tracking mode (IcePAP user manual pag. 88).

        :param signal: str
        :param mode: str
        """
        cmd = 'LTRACK {0} {1}'.format(signal, mode)
        self.send_cmd(cmd)

    def set_ecam_table(self, lpos, source='AXIS', dtype='FLOAT'):
        """
        Load the position list to the electronic cam table. The maximum memory
        size of the table is 81908 bytes. After to load the electronic cam
        is ON (IcePAP user manual pag. 65).

        :param lpos: [float]
        :param source: str
        :param dtype: str
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
        Clean the electronic cam table (Icepap user manual pag. 65).
        """
        self.send_cmd('ECAMDAT CLEAR')

    def get_ecam_table(self, dtype='FLOAT'):
        """
        Get the position table loaded on the electronic cam table (IcePAP user
        manual pag. 65).

        :param dtype: str
        :return: [float]
        """
        cmd = '?ECAMDAT {0} {1}'
        return self._get_dump_table(cmd, dtype)

    def set_list_table(self, lpos, cyclic=False, dtype='FLOAT'):
        """
        Load a position list table (Icepap user manual pag. 87).

        :param lpos: [float]
        :param cyclic: bool
        :param dtype: str
        """
        lushorts = self.get_ushort_list(lpos, dtype)
        # if len(lushorts) > 40954:
        #     raise ValueError('There is not enough memory to load the list.')

        cmd = '*LISTDAT {0} {1}'.format(['NOCYCLIC', 'CYCLIC'][cyclic], dtype)
        self.send_cmd(cmd)
        self._ctrl._comm.send_binary(lushorts)

    def clear_list_table(self):
        """
        Clean the position list table (Icepap user manual pag. 87).
        """
        self.send_cmd('LISTDAT CLEAR')

    def get_list_table(self, dtype='FLOAT'):
        """
        Get the position list table (IcePAP user manual pag. 87).

        :param dtype: str
        :return: [float]
        """
        cmd = '?LISTDAT {0} {1}'
        return self._get_dump_table(cmd, dtype)

    def set_parametric_table(self, lparam, lpos, lslope=None, mode='SPLINE',
                             param_type=FLOAT, pos_type=DWORD,
                             slope_type=FLOAT):
        """
        Method to set the parametric trajectory data (IcePAP user manual
        pag. 100).

        :param lparam: [float]
        :param lpos: [int]
        :param lslope: [float]
        :param mode: str [Linear, Spline, Cyclic]'
        :param param_type: str (Global Definitions in icepap.vdatalib)
        :param pos_type: str (Global Definitions in icepap.vdatalib)
        :param slope_type: str (Global Definitions in icepap.vdatalib)
        """
        data = vdata()
        data.append(lparam, ADDRUNSET, PARAMETER, format=param_type)
        data.append(lpos, self._axis_nr, POSITION, format=pos_type)
        if lslope is not None:
            data.append(lslope, self.addr, SLOPE, format=slope_type)

        bin_data = data.bin().flatten()
        lushorts = self.get_ushort_list(bin_data, dtype='BYTE')
        cmd = '*PARDAT {0}'.format(mode)
        self.send_cmd(cmd)
        self._ctrl._comm.send_binary(lushorts)

    def clear_parametric_table(self):
        """
        Clean the parametric trajectory table.
        """
        self.send_cmd('PARDAT CLEAR')

    def get_parametric_table(self):
        """
        Get the parametric table.

        :return: [[float]] ([parameter], [position], [slope])
        """
        MAX_SUBSET_SIZE = 20
        nr_points = int(self.send_cmd('?PARDAT NPTS')[0])
        if nr_points < MAX_SUBSET_SIZE:
            MAX_SUBSET_SIZE = nr_points
        if MAX_SUBSET_SIZE == 0:
            raise RuntimeError('There are not vlaues loaded on the '
                               'parametric table')
        lparam = []
        lpos = []
        lslope = []
        start_pos = 0
        cmd = '?PARDAT {0} {1}'
        packages = nr_points // MAX_SUBSET_SIZE
        for i in range(packages):
            raw_values = self.send_cmd(cmd.format(start_pos, MAX_SUBSET_SIZE))
            start_pos += MAX_SUBSET_SIZE
            for raw_value in raw_values:
                param, pos, slope = raw_value.strip().split()
                lparam.append(float(param))
                lpos.append(float(pos))
                lslope.append(float(slope))
        if (nr_points % MAX_SUBSET_SIZE) > 0:
            last_points = nr_points - start_pos
            raw_values = self.send_cmd(cmd.format(start_pos, last_points))
            for raw_value in raw_values:
                param, pos, slope = raw_value.strip().split()
                lparam.append(float(param))
                lpos.append(float(pos))
                lslope.append(float(slope))

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
        Get the allows commands (IcePAP user manual pag. 75).
        """
        ans = self.send_cmd('?HELP')
        print(('\n'.join(ans)))

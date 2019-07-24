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

__all__ = ['Info', 'Registers', 'State', 'TrackMode', 'Answers', 'Mode',
           'EdgeType', 'deprecated']

# TODO: Check the Mode, Answers, TrackMode, Info and Register classes.


def deprecated(alt=None):
    """
    Deprecation function (decorator) to mark future deprecated methods.
    @param alt: Alternative command in the new API.
    @return: decorated function with a deprecation message.
    """
    def _deprecated(f):
        from inspect import isclass, isfunction
        import warnings
        warnings.simplefilter("once")
        # Force warnings.warn() to omit the source code line in the message
        formatwarning_orig = warnings.formatwarning
        warnings.formatwarning = lambda msg, cat, fname, lineno, line=None: \
            formatwarning_orig(msg, cat, fname, lineno, line='')

        def new_func(*args, **kwargs):
            if isfunction(f):
                obj_type = 'method'
            elif isclass(f):
                obj_type = 'class'
            else:
                msg = "Decorated object is not a class nor a function."
                raise RuntimeError(msg)
            msg = "%s <%s> will be deprecated soon. " % (obj_type, f.__name__)
            msg += "Use new API %s <%s> instead." % (obj_type, alt)
            warnings.warn(msg, PendingDeprecationWarning, stacklevel=0)
            ans = f(*args, **kwargs)
            return ans
        return new_func
    return _deprecated


class Mode:
    """
    Icepap modes (IcePAP user manual pag. 22).
    """
    CONFIG, OPER, PROG, TEST, FAIL = 'CONFIG', 'OPER', 'PROG', 'TEST', 'FAIL'


class Answers:
    """
    Icepap answers values (str)
    """
    ON, OFF = "ON", "OFF"


class TrackMode:
    """
    Track modes (IcePAP user manual pag. 139).
    """
    SIMPLE, SMART, FULL = 'SIMPLE', 'SMART', 'FULL'


class EdgeType:
    """
    Edge type used on search routines. IcePAP user manual pag. 124
    """
    POSEDGE, NEGEDGE = 'POSEDGE', 'NEGEDGE'


class Info:
    """
    Icepap general namespace values.
    """
    INFOA, INFOB, INFOC = "INFOA", "INFOB", "INFOC"
    LOW, HIGH, LIMP = "LOW", "HIGH", "LIM+"
    LIMN, HOME, ENCAUX, ECAM = "LIM-", "HOME", "ENCAUX", "ECAM"
    INPAUX, SYNCAUX, ENABLE, ALARM = "INPAUX", "SYNCAUX", "ENABLE", "ALARM"
    READY, MOVING, BOOST, STEADY = "READY", "MOVING", "BOOST", "STEADY"
    Sources = [LOW, HIGH, LIMP, LIMN, HOME, ENCAUX, INPAUX, SYNCAUX, ENABLE,
               ALARM, READY, MOVING, BOOST, STEADY, ECAM]

    NORMAL, INVERTED = "NORMAL", "INVERTED"
    Polarity = [NORMAL, INVERTED]

    # NEW WITH FIRMWARE 2.x
    PULSE = 'PULSE'
    EcamSignals = [PULSE, LOW, HIGH]

    SearchSignals = [LIMP, LIMN, HOME, ENCAUX, INPAUX]


class Registers:
    """
    Icepap register namespace values.
    """
    INTERNAL, SYNC, INPOS, ENCIN = "INTERNAL", "SYNC", "INPOS", "ENCIN"
    IndexerRegisters = [INTERNAL, SYNC, INPOS, ENCIN]
    AXIS, INDEXER, EXTERR = "AXIS", "INDEXER", "EXTERR"
    SHFTENC, TGTENC, ENCIN, = "SHFTENC", "TGTENC", "ENCIN"
    INPOS, ABSENC = "INPOS", "ABSENC"
    MEASURE = 'MEASURE'
    PositionRegisters = [AXIS, INDEXER, EXTERR, SHFTENC, TGTENC, ENCIN,
                         INPOS, ABSENC]

    # NEW WITH FIRMWARE 2.x
    MEASURE, PARAM, CTRLENC, MOTOR = "MEASURE", "PARAM", "CTRLENC", "MOTOR"
    EcamSourceRegisters = [AXIS, MEASURE, PARAM, SHFTENC, TGTENC, CTRLENC,
                           ENCIN, INPOS, ABSENC, MOTOR]


class State:
    """
    Class to evaluate the status register.

    Table from Icepap User Manual - Section `Board Status Register`

    ========== ============ ===============================================
    0          PRESENT      1 = driver present
    1          ALIVE        1 = board responsive
    2-3        MODE         0 = OPER,
                            1 = PROG,
                            2 = TEST,
                            3 = FAIL.
    4-6        DISABLE      0 = enable\n
                            1 = axis not active\n
                            2 = hardware alarm\n
                            3 = remote rack disable input signal\n
                            4 = local rack disable switch\n
                            5 = remote axis disable input signal\n
                            6 = local axis disable switch\n
                            7 = software disable.
    7-8        INDEXER      0 = internal indexer\n
                            1 = in-system indexer\n
                            2 = external indexer\n
                            3 = n/a.
    9          READY        1 = ready to move
    10         MOVING       1 = axis moving
    11         SETTLING     1 = closed loop in settling phase
    12         OUTOFWIN     1 = axis out of settling window
    13         WARNING      1 = warning condition
    14-17      STOPCODE     0 = end of movement\n
                            1 = Stop\n
                            2 = Abort\n
                            3 = Limit+ reached\n
                            4 = Limit- reached\n
                            5 = Settling timeout\n
                            6 = Axis disabled\n
                            7 = n/a\n
                            8 = Internal failure\n
                            9 = Motor failure\n
                            10 = Power overload\n
                            11 = Driver overheating\n
                            12 = Close loop error\n
                            13 = Control encoder error\n
                            14 = n/a\n
                            15 = External alarm.
    18         LIMIT+       current value of the limit+ signal
    19         LIMIT-       current value of the limit- signal
    20         HOME         1 = Home switch reached (only in homing modes)
    21         5VPOWER      1 = Aux power supply on
    22         VERSERR      1 = inconsistency in firmware versions
    23         n/a          n/a
    24-31      INFO         In PROG mode: programming phase\n
                            In OPER mode: master indexer
    ========== ============ ===============================================
    """
    status_meaning = {'mode': {0: Mode.OPER,
                               1: Mode.PROG,
                               2: Mode.TEST,
                               3: Mode.FAIL},
                      'disable': {0: 'Enable',
                                  1: 'Axis not active',
                                  2: 'Hardware alarm',
                                  3: 'Remote rack disable input signal',
                                  4: 'Local rack disable switch',
                                  5: 'Remote axis disable input signal',
                                  6: 'Local axis disable switch',
                                  7: 'Software disable'},
                      'indexer': {0: 'Internal indexer',
                                  1: 'In-system indexer',
                                  2: 'External indexer',
                                  3: 'N/A'},
                      'stopcode': {0: 'End of movement',
                                   1: 'Stop',
                                   2: 'Abort',
                                   3: 'Limit+ reached',
                                   4: 'Limit- reached',
                                   5: 'Settling timeout',
                                   6: 'Axis disabled',
                                   7: 'N/A',
                                   8: 'Internal failure',
                                   9: 'Motor failure',
                                   10: 'Power overload',
                                   11: 'Driver overheating',
                                   12: 'Close loop error',
                                   13: 'Control encoder error',
                                   14: 'N/A',
                                   15: 'External alarm'},
                      'info': {}}

    def __init__(self, status_register):
        self._status_reg = status_register

    @property
    def status_register(self):
        return self._status_reg

    def is_present(self):
        """
        Check if the driver is present.

        :return: bool
        """
        val = self._status_reg >> 0
        val = val & 1
        return bool(val)

    def is_alive(self):
        """
        Check if the driver is alive.

        :return: bool
        """
        val = self._status_reg >> 1
        val = val & 1
        return bool(val)

    def get_mode_code(self):
        """
        Return the current mode.

        :return: str
        """
        val = self._status_reg >> 2
        val = val & 3
        return val

    def get_mode_str(self):
        """
        Return mode (str)

        :return: str
        """
        mode = self.get_mode_code()
        return self.status_meaning['mode'][mode]

    def is_disabled(self):
        """
        Check if the driver is disable.

        :return: bool
        """
        val = self._status_reg >> 4
        val = val & 7
        return val > 0

    def get_disable_code(self):
        """
        Get the disable code.

        :return: int
        """
        val = self._status_reg >> 4
        val = val & 7
        return val

    def get_disable_str(self):
        """
        Get the disable string.

        :return: str
        """
        disable_code = self.get_disable_code()
        return self.status_meaning['disable'][disable_code]

    def get_indexer_code(self):
        """
        Get the indexer code.

        :return: int
        """
        val = self._status_reg >> 7
        val = val & 3
        return val

    def get_indexer_str(self):
        """
        Get indexer string.

        :return: str
        """
        index_code = self.get_indexer_code()
        return self.status_meaning['indexer'][index_code]

    def is_ready(self):
        """
        Check if the driver is ready.

        :return: bool
        """
        val = self._status_reg >> 9
        val = val & 1
        return bool(val)

    def is_moving(self):
        """
        Check if the driver is moving.

        :return: bool
        """
        val = self._status_reg >> 10
        val = val & 1
        return bool(val)

    def is_settling(self):
        """
        Check if the driver is settling.

        :return: bool
        """
        val = self._status_reg >> 11
        val = val & 1
        return bool(val)

    def is_outofwin(self):
        """
        Check if the drive is out of the close loop window.

        :return: bool
        """
        val = self._status_reg >> 12
        val = val & 1
        return bool(val)

    def is_warning(self):
        """
        Check if the driver is in warning.

        :return: bool
        """
        val = self._status_reg >> 13
        val = val & 1
        return bool(val)

    def get_stop_code(self):
        """
        Get the stop code.

        :return: int
        """
        val = self._status_reg >> 14
        val = val & 15
        return val

    def get_stop_str(self):
        """
        Get the stop code string.

        :return: str
        """
        stop_code = self.get_stop_code()
        return self.status_meaning['stopcode'][stop_code]

    def is_limit_positive(self):
        """
        Check if the driver is touching the positive limit.

        :return: bool
        """
        val = self._status_reg >> 18
        val = val & 1
        return bool(val)

    def is_limit_negative(self):
        """
        Check if the driver is touching the positive limit.

        :return: bool
        """
        val = self._status_reg >> 19
        val = val & 1
        return bool(val)

    def is_inhome(self):
        """
        Check if the home switch was reached.

        :return: bool
        """
        val = self._status_reg >> 20
        val = val & 1
        return bool(val)

    def is_5vpower(self):
        """
        Check if the 5v auxiliary power is ON.

        :return: bool
        """
        val = self._status_reg >> 21
        val = val & 1
        return bool(val)

    def is_verserr(self):
        """
        Check if there is inconsistency in firmware versions.

        :return: bool
        """
        val = self._status_reg >> 22
        val = val & 1
        return bool(val)

    # TODO check why the documentation is not updated
    def is_poweron(self):
        """
        Check if the driver is powered ON.

        :return: bool
        """
        val = self._status_reg >> 23
        val = val & 1
        return bool(val)

    def get_info_code(self):
        """
        Get programming phase or master indexer accoding to the IcePAP mode.

        :return: str
        """
        val = self._status_reg >> 24
        val = val & 255
        return val

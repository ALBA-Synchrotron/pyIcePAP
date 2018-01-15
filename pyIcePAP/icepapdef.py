# ------------------------------------------------------------------------------
# This file is part of pyIcePAP (https://github.com/ALBA-Synchrotron/pyIcePAP)
#
# Copyright 2008-2017 CELLS / ALBA Synchrotron, Bellaterra, Spain
#
# Distributed under the terms of the GNU General Public License,
# either version 3 of the License, or (at your option) any later version.
# See LICENSE.txt for more info.
# ------------------------------------------------------------------------------

__all__ = ["IcepapInfo", "IcepapRegisters", "IcepapStatus",
           "IcepapTrackMode", "IcepapAnswers", "IcepapMode"]

class IcepapMode:
    CONFIG, OPER, PROG = "CONFIG", "OPER", "PROG"


class IcepapAnswers:
    ON, OFF = "ON", "OFF"


class IcepapTrackMode:
    """
    Track modes. icepap user manual, page 139
    """
    SIMPLE, SMART, FULL = 'SIMPLE', 'SMART', 'FULL'


class IcepapInfo:
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


class IcepapRegisters:
    INTERNAL, SYNC, INPOS, ENCIN = "INTERNAL", "SYNC", "INPOS", "ENCIN"
    IndexerRegisters = [INTERNAL, SYNC, INPOS, ENCIN]
    AXIS, INDEXER, EXTERR = "AXIS", "INDEXER", "EXTERR"
    SHFTENC, TGTENC, ENCIN, = "SHFTENC", "TGTENC", "ENCIN"
    INPOS, ABSENC = "INPOS", "ABSENC"
    PositionRegisters = [AXIS, INDEXER, EXTERR, SHFTENC, TGTENC, ENCIN,
                         INPOS, ABSENC]

    # NEW WITH FIRMWARE 2.x
    MEASURE, PARAM, CTRLENC, MOTOR = "MEASURE", "PARAM", "CTRLENC", "MOTOR"
    EcamSourceRegisters = [AXIS, MEASURE, PARAM, SHFTENC, TGTENC, CTRLENC,
                           ENCIN, INPOS, ABSENC, MOTOR]

    """
    Table from Icepap User Manual - Section 'Board Status Register'
    ---------------------------------------------------------------
    0 PRESENT      : 1 = driver present
    1 ALIVE        : 1 = board responsive
    2-3 MODE       : 0 = OPER
                     1 = PROG
                     2 = TEST
                     3 = FAIL
    4-6 DISABLE    : 0 = enable
                     1 = axis not active
                     2 = hardware alarm
                     3 = remote rack disable input signal
                     4 = local rack disable switch
                     5 = remote axis disable input signal
                     6 = local axis disable switch
                     7 = software disable
    7-8 INDEXER    : 0 = internal indexer
                     1 = in-system indexer
                     2 = external indexer
                     3 = n/a
    9 READY        : 1 = ready to move
    10 MOVING      : 1 = axis moving
    11 SETTLING    : 1 = closed loop in settling phase
    12 OUTOFWIN    : 1 = axis out of settling window
    13 WARNING     : 1 = warning condition
    14-17 STOPCODE : 0 = end of movement
                     1 = Stop
                     2 = Abort
                     3 = Limit+ reached
                     4 = Limit- reached
                     5 = Settling timeout
                     6 = Axis disabled
                     7 = n/a
                     8 = Internal failure
                     9 = Motor failure
                    10 = Power overload
                    11 = Driver overheating
                    12 = Close loop error
                    13 = Control encoder error
                    14 = n/a
                    15 = External alarm
    18 LIMIT+      : current value of the limit+ signal
    19 LIMIT-      : current value of the limit- signal
    20 HOME        : 1 = Home switch reached (only in homing modes)
    21 5VPOWER     : 1 = Aux power supply on
    22 VERSERR     : 1 = inconsistency in firmware versions
    23             : n/a
    24-31 INFO     : In PROG mode: programming phase
                     In OPER mode: master indexer
    """


class IcepapStatus:
    status_keys = [
        'present',
        'alive',
        'mode',
        'disable',
        'indexer',
        'ready',
        'moving',
        'settling',
        'outofwin',
        'warning',
        'stopcode',
        'lim+',
        'lim-',
        'home',
        '5vpower',
        'verserr',
        'poweron',
        'info']

    status_meaning = {'present': {0: 'No', 1: 'Yes'},
                      'alive': {0: 'No', 1: 'Yes'},
                      'mode': {0: 'OPER',
                               1: 'PROG',
                               2: 'TEST',
                               3: 'FAIL'},
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
                      'ready': {0: 'No', 1: 'Yes'},
                      'moving': {0: 'No', 1: 'Yes'},
                      'settling': {0: 'No', 1: 'Yes'},
                      'outofwin': {0: 'No', 1: 'Yes'},
                      'warning': {0: 'No', 1: 'Yes'},
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
                      'lim+': {0: 'No', 1: 'Yes'},
                      'lim-': {0: 'No', 1: 'Yes'},
                      'home': {0: 'No', 1: 'Yes'},
                      '5vpower': {0: 'No', 1: 'Yes'},
                      'verserr': {0: 'No', 1: 'Yes'},
                      'poweron': {0: 'No', 1: 'Yes'},
                      'info': {}}

    @staticmethod
    def isPresent(register):
        val = register >> 0
        val = val & 1
        return val

    @staticmethod
    def isAlive(register):
        val = register >> 1
        val = val & 1
        return val

    @staticmethod
    def getMode(register):
        val = register >> 2
        val = val & 3
        return val

    @staticmethod
    def isDisabled(register):
        val = register >> 4
        val = val & 7
        return val

    @staticmethod
    def getIndexer(register):
        val = register >> 7
        val = val & 3
        return val

    @staticmethod
    def isReady(register):
        val = register >> 9
        val = val & 1
        return val

    @staticmethod
    def isMoving(register):
        val = register >> 10
        val = val & 1
        return val

    @staticmethod
    def isSettling(register):
        val = register >> 11
        val = val & 1
        return val

    @staticmethod
    def isOutOfWin(register):
        val = register >> 12
        val = val & 1
        return val

    @staticmethod
    def isWarning(register):
        val = register >> 13
        val = val & 1
        return val

    @staticmethod
    def getStopCode(register):
        val = register >> 14
        val = val & 15
        return val

    @staticmethod
    def getLimitPositive(register):
        val = register >> 18
        val = val & 1
        return val

    @staticmethod
    def getLimitNegative(register):
        val = register >> 19
        val = val & 1
        return val

    @staticmethod
    def inHome(register):
        val = register >> 20
        val = val & 1
        return val

    @staticmethod
    def is5VPower(register):
        val = register >> 21
        val = val & 1
        return val

    @staticmethod
    def isVersErr(register):
        val = register >> 22
        val = val & 1
        return val

    @staticmethod
    def isPowerOn(register):
        val = register >> 23
        val = val & 1
        return val

    @staticmethod
    def getInfo(register):
        val = register >> 24
        val = val & 255
        return val

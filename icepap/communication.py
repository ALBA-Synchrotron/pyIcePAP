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

import array
import struct
import threading

from .tcp import TCP, Timeout


__all__ = ['IcePAPCommunication']


class IcePAPCommunication:
    """
    Class implementing the communication layer for IcePAP motion controller.
    It bases on the socket communication. For the Serial communication see
    manual.
    """

    def __init__(self, host, port=5000, timeout=3):
        self._sock = TCP(host, port, timeout=timeout)
        self._sock.connect()
        self._lock = threading.Lock()
        self.multiline_answer = False

    @property
    def host(self):
        return self._sock.host

    @property
    def port(self):
        return self._sock.port

    @property
    def timeout(self):
        return self._sock.timeout

    def send_cmd(self, cmd):
        """
        Method to send commands to the IcePAP controller. It uses acknowledge
        communication (IcePAP User Manual pag. 37).

        :param cmd: Command without acknowledge character and CR and/or LF.
        :return: None or list of string without the command and the CRLF.
        """
        self.multiline_answer = False
        cmd.upper().strip()
        flg_read_cmd = '?' in cmd
        flg_ecamdat_cmd = '*ECAMDAT' in cmd
        flg_listdat_cmd = '*LISTDAT' in cmd
        flg_pardat_cmd = '*PARDAT' in cmd
        use_ack = False
        # The acknowledge character does not have effect on read command.
        # There is a bug on some commands PROG, *PROG, RESET(3.17 does not
        # have problem) and command start by ":"
        bad_cmds = ('PROG', '*PROG', 'RESET', ':')

        if flg_read_cmd or cmd.startswith(bad_cmds) or flg_ecamdat_cmd or \
                flg_listdat_cmd or flg_pardat_cmd:
            cmd = '{0}\r'.format(cmd)
        else:
            cmd = '#{0}\r'.format(cmd)
            use_ack = True

        if '?' in cmd or '#' in cmd:
            wait_ans = True
        else:
            wait_ans = False

        with self._lock:
            # The write command is inside the lock on purpose. The issue is, if
            # two threads write very close in time, the OS might join the two
            # packets together. Experience shows the hardware does not like
            # that. Actually the TCP object disables Nagle algorithm
            # (TCP_NODELAY) so there should be no problem putting write outside
            # the lock. But it was decided to be conservative anyway
            self._sock.write(cmd.encode())
            if wait_ans:
                ans = self._sock.read(8096).decode()
                nb_dollars = ans.count("$")
                if nb_dollars == 1:
                    ans += self._sock.readline(eol=b"$").decode()
                    try:
                        ans += self._sock.readline(eol=b"\n",
                                                   timeout=0.001).decode()
                    except Timeout:
                        ans += '\n'
            else:
                ans = None

        msg = 'Error sending command, IcePAP answered {0}'
        if use_ack:
            if 'OK' not in ans:
                raise RuntimeError(msg.format(ans))
            else:
                result = None
        else:
            if ans is None:
                result = ans
            elif '$' in ans:
                self.multiline_answer = True
                # Multi lines
                ans = ans.split('$')[1]
                lines = ans.split('\n')[1:-1]
                # remove CR
                result = [line.split('\r')[0] for line in lines]
            else:
                ans = ans.split('\r\n')[0]
                result = ans.split()[1:]
                if len(result) == 0:
                    result = None
                elif result[0] == 'ERROR':
                    raise RuntimeError(msg.format(ans))

        return result

    def send_binary(self, ushort_data):
        """
        Method to send a binary data to the IcePAP controller.

        :param ushort_data: Data converted to a unsigned short list.
        """
        # Prepare Metadata header
        startmark = 0xa5aa555a
        nworddata = len(ushort_data)
        checksum = sum(ushort_data)
        maskedchksum = checksum & 0xffffffff
        data = array.array('H', ushort_data)

        str_startmark = struct.pack('L', startmark)[:4]
        str_nworddata = struct.pack('L', nworddata)[:4]
        str_maskedchksum = struct.pack('L', maskedchksum)[:4]
        str_data = data.tobytes()
        str_bin = str_startmark + str_nworddata + str_maskedchksum + str_data
        str_bin += b'\r'

        self._sock.write(str_bin)

    def disconnect(self):
        """
        Method to close the communication
        """
        self._sock.close()

    def is_connected(self):
        return self._sock.connected()

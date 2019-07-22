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

import socket
import threading
import struct
import time
import array
import logging

__all__ = ['IcePAPCommunication']

ICEPAP_ENCODING = 'latin-1'


def comm_error_handler(f):
    """
    Error handling function (decorator).

    @param f: target function.
    @return: decorated function with error handling.
    """
    def new_func(*args, **kwargs):
        try:
            ans = f(*args, **kwargs)
            return ans
        except Exception as e:
            msg = 'Problem with the communication. Verify ' \
                  'the hardware. Error: {0}'.format(e)
            raise RuntimeError(msg)
    return new_func


class IcePAPCommunication:
    """
    Class implementing the communication layer for IcePAP motion controller.
    It bases on the socket communication. For the Serial communication see
    manual.
    """
    def __init__(self, host, port=5000, timeout=3):
        self._comm = SocketCom(host=host, port=port, timeout=timeout)

    @property
    def host(self):
        return self._comm.host

    @property
    def port(self):
        return self._comm.port

    @property
    def timout(self):
        return self._comm.timeout

    def send_cmd(self, cmd):
        """
        Method to send commands to the IcePAP controller. It uses acknowledge
        communication (IcePAP User Manual pag. 37).

        :param cmd: Command without acknowledge character and CR and/or LF.
        :return: None or list of string without the command and the CRLF.
        """
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

        ans = self._comm.send_cmd(cmd)
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
        self._comm.send_binary(ushort_data=ushort_data)

    def disconnect(self):
        """
        Method to close the communication
        """
        self._comm.disconnect()

    def is_conneted(self):
        return self._comm.connected


# -----------------------------------------------------------------------------
#                           Socket Communication
# -----------------------------------------------------------------------------
class SocketCom:
    """
    Class which implements the Socket communication layer with ASCii interface
    for IcePAP motion controllers.
    """
    def __init__(self, host, port=5000, timeout=3.0):
        log_name = '{0}.SocketCom'.format(__name__)
        self.log = logging.getLogger(log_name)
        self._socket = None
        self._lock = threading.Lock()
        self._stop_thread = False
        self._connect_thread = None
        self._connection_error = ''
        self.host = host
        self.port = port
        self.timeout = timeout
        self.connected = False

        # Start the connection thread
        self._start_thread(wait=False)
        self._connect_thread.join()
        if not self.connected and self._connection_error != '':
            raise RuntimeError(self._connection_error)

    def __del__(self):
        self.disconnect()

    def disconnect(self):
        self._socket.close()
        self.connected = False
        self._stop_thread = True
        self._connect_thread.join()

    @comm_error_handler
    def send_cmd(self, cmd):
        """
        Implementation of the API send command via Socket communication layer.

        :param cmd: string Icepap command.
        :return: Raw string answer for the requested commmand.
        """
        wait_answer = ('#' in cmd) or ('?' in cmd)
        return self._send_data(cmd, wait_answer=wait_answer)

    @comm_error_handler
    def send_binary(self, ushort_data):
        """
        Send data in binary mode.

        :param ushort_data: binary data.
        :return:
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
        str_data = data.tostring()
        str_bin = str_startmark + str_nworddata + str_maskedchksum + str_data
        str_bin += b'\r'
        self._send_data(str_bin, wait_answer=False, encoding=False)

    def _start_thread(self, wait=True):
        self.log.debug('Start thread {0}'.format(self._connect_thread))
        self._connect_thread = threading.Thread(target=self._try_to_connect,
                                                args=[wait])
        self._connect_thread.setDaemon(True)
        self._connect_thread.start()

    def _try_to_connect(self, wait=True):
        self.connected = False
        self._connection_error = ''
        sleep_time = self.timeout / 10.0
        if self._socket is not None:
            try:
                self._socket.close()
            except Exception:
                pass
        while not self._stop_thread:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(self.timeout)
            NOLINGER = struct.pack('ii', 1, 0)
            # TODO: protect EBADF [Errno 9] during reboot
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER,
                                    NOLINGER)
            try:
                self._socket.connect((self.host, self.port))
                self.connected = True
                break
            except socket.timeout:
                self.log.debug('Fail to connect', exc_info=True)
                if not wait:
                    self._connection_error = \
                        'Timeout error! Check if {} is ON'.format(self.host)
                    break
                time.sleep(sleep_time)
            except OSError as e:
                self._connection_error = \
                    'Fail to connect {}:{}. ' \
                    'Error: {}'.format(self.host, self.port, e.strerror)
                break

    def _send_data(self, data, wait_answer=True, size=8192, encoding=True):
        if encoding:
            raw_data = data.encode(ICEPAP_ENCODING)
        else:
            raw_data = data

        if not self.connected:
            self._start_thread()
            raise RuntimeError('Connection error: No connection with the '
                               'Icepap sytem')

        try:
            with self._lock:
                self.log.debug('RAW_DATA to send: {0}'.format(repr(raw_data)))
                raw_data_size = len(raw_data)
                if raw_data_size > size:
                    # TODO: use python logging
                    self.log.debug('Send multi-lines')
                    n = int(raw_data_size / size)
                    start = 0
                    for i in range(n):
                        end = (i+1) * size
                        self._socket.sendall(raw_data[start:end])
                        start = end
                    if int(raw_data_size % size) > 0:
                        self._socket.sendall(raw_data[start:])
                else:
                    self._socket.sendall(raw_data)
                if wait_answer:
                    answer = self._socket.recv(size)
                    if answer.count(b'$') > 0:
                        # -----------------------------------------------------
                        # WORKAROUND
                        # -----------------------------------------------------
                        # AS IT IS SAID IN
                        # https://docs.python.org/3/howto/sockets.html
                        # SECTION "Using a Socket"
                        #
                        # A protocol like HTTP uses a socket for only one
                        # transfer. The client sends a request, the reads a
                        # reply. That's it. The socket is discarded. This
                        # means that a client can detect the end of the reply
                        # by receiving 0 bytes.
                        #
                        # But if you plan to reuse your socket for further
                        # transfers, you need to realize that there is no
                        # "EOT" (End of Transfer) on a socket. I repeat: if a
                        # socket send or recv returns after handling 0 bytes,
                        # the connection has been broken. If the connection
                        # has not been broken, you may wait on a recv forever,
                        # because the socket will not tell you that there's
                        # nothing more to read (for now). Now if you think
                        # about that a bit, you'll come to realize a
                        # fundamental truth of sockets: messages must either
                        # be fixed length (yuck), or be delimited (shrug), or
                        # indicate how long they are (much better), or end by
                        # shutting down the connection. The choice is entirely
                        # yours, (but some ways are righter than others).
                        #
                        # WE SHOULD WAIT UNTIL THE TERMINATOR CHAR '$' IS
                        # FOUND
                        while answer.count(b'$') < 2:
                            answer = answer + self._socket.recv(size)
                    self.log.debug('RAW_DATA read: {0}'.format(repr(answer)))
                    return answer.decode(ICEPAP_ENCODING)
        except Exception as e:
            self._start_thread()
            raise RuntimeError('Communication error: Error sending command to '
                               'the IcePAP ({0})'.format(e))

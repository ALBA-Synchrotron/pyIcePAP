# ------------------------------------------------------------------------------
# This file is part of pyIcePAP (https://github.com/ALBA-Synchrotron/pyIcePAP)
#
# Copyright 2008-2017 CELLS / ALBA Synchrotron, Bellaterra, Spain
#
# Distributed under the terms of the GNU General Public License,
# either version 3 of the License, or (at your option) any later version.
# See LICENSE.txt for more info.
#
# You should have received a copy of the GNU General Public License
# along with pyIcePAP. If not, see <http://www.gnu.org/licenses/>.
# ------------------------------------------------------------------------------

from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_LINGER
from threading import Thread, Lock
import struct
import time
import array
from future import *

_imported_serial = False
try:
    from serial import Serial
    _imported_serial = True
except ImportError:
    Serial = object


__all__ = ['CommType', 'IcePAPCommunication']


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
        except Exception, e:
            msg = ('Problem with the communication. Verify the hardware. '
                   'Error: %s' % e)
            raise RuntimeError(msg)
    return new_func


class CommType(object):
    Serial = 1
    Socket = 2


# TODO Implement logging

class IcePAPCommunication(object):
    """
    Abstract class which provides a certain communication layer to the IcePAP
    motion controller.
    """
    def __init__(self, comm_type, *args, **kwargs):
        if comm_type == CommType.Serial:
            self._comm = SerialCom(*args, **kwargs)
            self._comm_type = CommType.Serial
        elif comm_type == CommType.Socket:
            self._comm = SocketCom(*args, **kwargs)
            self._comm_type = CommType.Socket
        else:
            raise ValueError()

    def send_cmd(self, cmd):
        """
        Method to send commands to the IcePAP controller. Use acknowledge
        communication. (IcePAP User Manual pag. 37)
        :param cmd: Command without acknowledge character and carriage
                    return (\r) and/or line feed (\n)
        :return: None or list of string without the command and the CRLF.
                 example: 1:move 100 -> None
                          1:?Pos -> 100
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
                if result[0] == 'ERROR':
                    raise RuntimeError(msg.format(ans))

        return result

    def send_binary(self, ushort_data):
        """
        Method to send a binary data to the IcePAP
        :param ushort_data: Data converted to a unsigned short list
        :return:
        """
        self._comm.send_binary(ushort_data=ushort_data)

    def get_comm_type(self):
        return self._comm_type


# -----------------------------------------------------------------------------
#                           Serial Communication
# -----------------------------------------------------------------------------
class SerialCom(Serial):
    """
    Class which implements the Serial communication layer with ASCII interface
    for IcePAP motion controllers.
    """
    def __init__(self, timeout=2):
        if not _imported_serial:
            raise RuntimeError('The serial module was not imported.')
        Serial.__init__(self, timeout=timeout)

    @comm_error_handler
    def send_cmd(self, cmd):
        self.flush()
        self.write(cmd)
        time.sleep(0.02)
        # TODO investigate why we need to read two times
        newdata = self.readline()
        newdata = self.readline()
        return newdata

    # TODO analise the code
    # def readline(self, maxsize=None, timeout=2):
    #     """maxsize is ignored, timeout in seconds is the max time that is
    #     way for a complete line"""
    #     tries = 0
    #
    #     while True:
    #         self.buf += self.tty.read()
    #         pos = self.buf.find('\n')
    #         if pos >= 0:
    #             line, self.buf = self.buf[:pos + 1], self.buf[pos + 1:]
    #             return line
    #         tries += 1
    #         # if tries * self.timeout > timeout:
    #     # print 'exit bucle'
    #     #       break
    #     line, self.buf = self.buf, ''
    #     return line

    @comm_error_handler
    def send_binary(self, ushort_data):
        raise NotImplemented


# -----------------------------------------------------------------------------
#                           Socket Communication
# -----------------------------------------------------------------------------
class SocketCom(object):
    """
    Class which implements the Socket communication layer with ASCii interface
    for IcePAP motion controllers.
    """
    def __init__(self, host, port=5000, timeout=3.0):
        self._socket = None
        self._host = host
        self._port = port
        self._timeout = timeout
        self._connected = False
        self._lock = Lock()
        self._stop_thread = False
        self._connect_thread = None
        self._start_thread()
        self._connect_thread.join()

    def __del__(self):
        self._stop_thread = True
        self._connect_thread.join()

    @comm_error_handler
    def send_cmd(self, cmd):
        wait_answer = ('#' in cmd) or ('?' in cmd)
        return self._send_data(cmd, wait_answer=wait_answer)

    @comm_error_handler
    def send_binary(self, ushort_data):
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
        str_bin = '{0}{1}{2}{3}\r'.format(str_startmark, str_nworddata,
                                          str_maskedchksum, str_data)
        self._send_data(str_bin, wait_answer=False)

    def _start_thread(self):
        # print('Start thread %r ' % self._connect_thread)
        self._connect_thread = Thread(target=self._try_to_connect)
        self._connect_thread.setDaemon(True)
        self._connect_thread.start()

    def _try_to_connect(self):
        self._connected = False
        sleep_time = self._timeout / 10
        if self._socket is not None:
            try:
                self._socket.close()
            except Exception:
                pass
        while not self._stop_thread:
            self._socket = socket(AF_INET, SOCK_STREAM)
            self._socket.settimeout(self._timeout)
            NOLINGER = struct.pack('ii', 1, 0)
            # TODO: protect EBADF [Errno 9] during reboot
            self._socket.setsockopt(SOL_SOCKET, SO_LINGER, NOLINGER)
            try:
                self._socket.connect((self._host, self._port))
                self._connected = True
                break
            except Exception:
                time.sleep(sleep_time)

    def _send_data(self, raw_data, wait_answer=True, size=8192):
        if not self._connected:
            self._start_thread()
            raise RuntimeError('Connection error: No connection with the '
                               'Icepap sytem')

        try:
            with self._lock:
                # TODO: use python logging
                print('\tRAW_DATA to send: %r' % raw_data)
                raw_data_size = len(raw_data)
                if raw_data_size > size:
                    # TODO: use python logging
                    # print('Send multitimes')
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
                    if answer.count("$") > 0:
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
                        while answer.count('$') < 2:
                            answer = answer + self._socket.recv(size)
                    # TODO: use python logging
                    print('\tRAW_DATA read: %r' % answer)
                    return answer
        except Exception as e:
            self._start_thread()
            raise RuntimeError('Communication error: Error sending command to '
                               'the IcePAP ({0})'.format(e))


class EthIcePAPCommunication(IcePAPCommunication):
    def __init__(self, host, port=5000, timeout=3):
        IcePAPCommunication.__init__(self, CommType.Socket, host=host,
                                     port=port, timeout=timeout)

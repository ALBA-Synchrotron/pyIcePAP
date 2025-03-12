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
import os
import time
import errno
import select
import socket
import logging
import functools

__all__ = ['TCP']

Timeout = socket.timeout
OPENING, OPEN, CLOSED = range(3)


BLOCK_SIZE = 8192


ERR_MAP = {
    errno.ECONNREFUSED: ConnectionRefusedError,
    errno.ECONNRESET: ConnectionResetError,
    errno.ECONNABORTED: ConnectionAbortedError,
    errno.EPIPE: BrokenPipeError,
    errno.EBADF: OSError,
}


def to_error(err):
    if err:
        return ERR_MAP.get(err, ConnectionError)(err, os.strerror(err))


def create_connection(host, port):
    sock = socket.socket()
    sock.setblocking(False)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    res = sock.connect_ex((host, port))
    allowed_results = [0, errno.EINPROGRESS]
    # Non-blocking sockets on Windows give the WSAEWOULDBLOCK when opening.
    # Add this to allowed list.
    if hasattr(errno, "WSAEWOULDBLOCK"):
        allowed_results.append(errno.WSAEWOULDBLOCK)
    if res not in allowed_results:
        raise to_error(res)
    return sock


def wait_open(sock, timeout=None):
    if timeout is None:
        _, w, _ = select.select((), (sock,), ())
    elif timeout >= 0:
        _, w, _ = select.select((), (sock,), (), timeout)
    else:
        raise Timeout("timeout trying to connect")
    if w:
        err = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
        if err:
            raise to_error(err)
    else:
        raise Timeout("timeout trying to connect")


def stream(sock, buffer_size=BLOCK_SIZE, timeout=None):
    readers = sock,
    while True:
        start = time.monotonic()
        r, _, _ = select.select(readers, (), (), timeout)
        end = time.monotonic()
        if timeout is not None:
            timeout -= start - end
        if (timeout is not None and timeout <= 0) or not r:
            raise Timeout("read timeout")
        data = sock.recv(buffer_size)
        if not data:
            break
        yield data


def check_open(f):
    @functools.wraps(f)
    def wrapper(self, *args, **kwargs):
        state = self._state
        if state is CLOSED:
            raise to_error(errno.EBADF)
        elif state is OPENING:
            self.wait_open()
        return f(self, *args, **kwargs)
    return wrapper


def close_on_error(f):
    @functools.wraps(f)
    def wrapper(self, *args, **kwargs):
        try:
            return f(self, *args, **kwargs)
        except BaseException:
            self.close()
            raise
    return wrapper


class RawTCP:

    def __init__(self, host, port, eol=b"\n", timeout=None):
        self.eol = eol
        self.timeout = timeout
        self._buffer = b""
        self._sock = None
        # create a non blocking socket
        self._state = OPENING
        self._connection_time = time.monotonic()
        self._sock = create_connection(host, port)

    def __del__(self):
        self.close()

    def wait_open(self):
        if self._state is OPEN:
            return
        elif self._state is CLOSED:
            raise OSError("would block forever")
        elif self._state is OPENING:
            timeout = self.timeout
            if timeout is not None:
                timeout -= time.monotonic() - self._connection_time
                timeout = max(0, timeout)
            wait_open(self._sock, timeout=timeout)
        self._state = OPEN

    @close_on_error
    def _write(self, data):
        for start in range(0, len(data), BLOCK_SIZE):
            _, w, _ = select.select((), (self._sock,), (), self.timeout)
            if not w:
                raise to_error(errno.EPIPE)
            self._sock.sendall(data[start: start + BLOCK_SIZE])

    @close_on_error
    def _read(self, n, timeout=None):
        if self._buffer:
            data, self._buffer = self._buffer, b""
            return data
        timeout = self.timeout if timeout is None else timeout
        r, _, _ = select.select((self._sock,), (), (), timeout)
        if r:
            data = self._sock.recv(BLOCK_SIZE)
            if not data:
                raise ConnectionError("remote end closed")
            return data
        else:
            raise Timeout("timeout reading from socket")

    @close_on_error
    def _readline(self, eol=None, timeout=None):
        eol = self.eol if eol is None else eol
        timeout = self.timeout if timeout is None else timeout
        data, eo, left = self._buffer.partition(eol)
        if eo:
            self._buffer = left
            return data + eo
        for data in stream(self._sock, timeout=timeout):
            self._buffer += data
            data, eo, left = self._buffer.partition(eol)
            if eo:
                self._buffer = left
                return data + eo
        else:
            raise ConnectionError("remote end closed")

    def state(self):
        return self._state

    def close(self):
        self._state = CLOSED
        self._buffer = b""
        if self._sock is not None:
            try:
                self._sock.shutdown(socket.SHUT_RDWR)
                self._sock.close()
            except OSError:
                pass
            finally:
                self._sock = None

    @check_open
    def write(self, data):
        self._write(data)

    @check_open
    def read(self, n, timeout=None):
        return self._read(n, timeout=timeout)

    @check_open
    def readline(self, eol=None, timeout=None):
        return self._readline(eol=eol, timeout=timeout)

    @check_open
    def write_read(self, data, n, timeout=None):
        self._write(data)
        return self._read(n, timeout=timeout)

    @check_open
    def write_readline(self, data, eol=None, timeout=None):
        self._write(data)
        return self._readline(eol=eol, timeout=timeout)


def ensure_connection(f):
    @functools.wraps(f)
    def wrapper(self, *args, **kwargs):
        made_connection = self._ensure_connected()
        try:
            return f(self, *args, **kwargs)
        except Timeout:
            raise
        except OSError:
            self.close()
            if made_connection:
                raise
            self._ensure_connected()
            return f(self, *args, **kwargs)
    return wrapper


class TCP:

    def __init__(self, host, port, eol=b"\n", timeout=None):
        self.host = host
        self.port = port
        self.eol = eol
        self.timeout = timeout
        self.connection_counter = 0
        self._sock = None
        logger_name = "{}.TCP.{}".format(__name__, host)
        self._log = logging.getLogger(logger_name)

    def connected(self):
        return self._sock is not None and self._sock.state() is OPEN

    def _ensure_connected(self):
        if self.connected():
            return False
        self._sock = RawTCP(
            self.host, self.port, eol=self.eol, timeout=self.timeout
        )
        self._sock.wait_open()
        self.connection_counter += 1
        self._log.debug("reconnecting #%d...", self.connection_counter)
        return True

    def connect(self):
        self._ensure_connected()

    def close(self):
        if self._sock is not None:
            self._sock.close()

    @ensure_connection
    def write(self, data):
        self._log.debug("write -> %r", data)
        self._sock.write(data)

    @ensure_connection
    def read(self, n, timeout=None):
        reply = self._sock.read(n, timeout=timeout)
        self._log.debug("read <- %r", reply)
        return reply

    @ensure_connection
    def write_read(self, data, n, timeout=None):
        self._log.debug("write_read -> %r", data)
        reply = self._sock.write_read(data, n, timeout=timeout)
        self._log.debug("write_read <- %r", reply)
        return reply

    @ensure_connection
    def write_readline(self, data, eol=None, timeout=None):
        self._log.debug("write_readline -> %r", data)
        reply = self._sock.write_readline(data, eol=eol, timeout=timeout)
        self._log.debug("write_readline <- %r", reply)
        return reply

    @ensure_connection
    def readline(self, eol=None, timeout=None):
        return self._sock.readline(eol=eol, timeout=timeout)

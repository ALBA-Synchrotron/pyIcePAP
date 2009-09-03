import socket
import struct
import errno
import time
import icepapdef
from IcePAP import *
from threading import Thread

class ReconnectThread(Thread):
    def __init__(self,icepap,sleeptime):
        Thread.__init__(self)
        self.icepap = icepap
        self.sleeptime = sleeptime

    def run(self):
        while True:
            if not self.icepap.connected:
                if self.icepap.DEBUG:
                    print "Reconnect Thread: Trying to reconnect"
                self.icepap.try_to_connect()
            time.sleep(self.sleeptime)
        
class EthIcePAP(IcePAP):

    def __init__(self,host,port,timeout=3,log_path=None):
        IcePAP.__init__(self,host,port,timeout,log_path)
        self.connected = 0
        self.DEBUG = False
        self.reconnect_thread = ReconnectThread(self,self.timeout/10.0)
        self.reconnect_thread.setDaemon(True)
        self.reconnect_thread.start()

    def connect(self):
        total_sleep = 0
        inc = self.timeout/10.0
        while (not self.connected) and (total_sleep < self.timeout):
            time.sleep(inc)
            total_sleep += inc
        if self.connected:
            return True
        raise IcePAPException(IcePAPException.ERROR, "Connection error","no connection with the Icepap sytem")
        
            
    def sendWriteReadCommand(self, cmd, size = 8192):
        if not self.connected:
            raise IcePAPException(IcePAPException.ERROR, "Connection error","no connection with the Icepap sytem")
        try:
            #print "sendWriteReadCommand"
            message = cmd
            cmd = cmd + "\n"
            self.lock.acquire()
            self.IcPaSock.send(cmd)
            data = self.IcPaSock.recv(size)
            if data.count("$") > 0:
                ################################################
                # WORKAROUND
                ################################################
                # AS IT IS SAID IN http://www.amk.ca/python/howto/sockets/
                # SECTION "3 Using a Socket"
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
                while data.count('$') < 2:
                    data = data + self.IcPaSock.recv(size)
                ################################################

            self.lock.release()
            message = message + "\t\t[ " + data + " ]"
            self.writeLog(message)
            if self.DEBUG:
                print "\t\tSEND: %s\t\tRECEIVE: %s" % (cmd,data)
            return data
        except socket.timeout, msg:
            if self.DEBUG:
                print "socket TIME OUT"
            self.writeLog(message + " " + str(msg))  
            self.lock.release()
            self.disconnect()   
            iex = IcePAPException(IcePAPException.TIMEOUT, "Connection Timeout",msg)
            raise iex
        except socket.error, msg:
            if self.DEBUG:
                print "socket ERROR: %s"%msg
            a,b,c=sys.exc_info()
            e,f=b
            self.writeLog(message + " " + str(sys.exc_info()))
            self.lock.release()  
            self.disconnect()   
            if e==errno.ECONNRESET or e==errno.EPIPE:
                    #print "Disconnected socket\n"
                    #self.connect_retry()
                    pass
            else:
                iex = IcePAPException(IcePAPException.ERROR, "Error sending command to the Icepap",msg)
                raise iex
        

    
    def sendWriteCommand(self, cmd, prepend_ack=True):
        if not self.connected:
            raise IcePAPException(IcePAPException.ERROR, "Connection error","no connection with the Icepap sytem")

        # BUG FOUND DOING AND ACK TO ALL COMMANDS BY DEFAULT
        if cmd.startswith('PROG') or cmd.startswith('*PROG') or cmd.startswith(':'):
            prepend_ack = False

        if prepend_ack:
            ack_cmd = cmd
            if cmd.find('#') != 0:
                ack_cmd = '#'+cmd
            ans = self.sendWriteReadCommand(ack_cmd)
            if ans.find('OK') == -1:
                msg = 'Error sending command %s, icepap answered %s' % (cmd,ans)
                iex = IcePAPException(IcePAPException.ERROR, "SendWriteCommand failed the 'ACK'", msg)
                raise iex
            return
        try:
            message = cmd
            cmd = cmd + "\n"
            self.lock.acquire()
            self.IcPaSock.send(cmd)
            self.writeLog(message)
            self.lock.release()
            if self.DEBUG:
                print "SEND:>%s<" % cmd
        except socket.timeout, msg:
            if self.DEBUG:
                print "socket TIME OUT"
            self.writeLog(message + " " + msg)      
            self.lock.release()
            self.disconnect()
            iex = IcePAPException(IcePAPException.TIMEOUT, "Connection Timeout",msg)
            raise iex            
        except socket.error, msg:
            if self.DEBUG:
                print "socket ERROR: %s"%msg
            self.writeLog(message + " " + str(sys.exc_info()))
            self.lock.release()  
            self.disconnect()
            #print "Unexpected error:", sys.exc_info()
            iex = IcePAPException(IcePAPException.ERROR, "Error sending command to the Icepap",msg)
            raise iex   
            
        
    def sendData(self, data):
        try:
            self.lock.acquire()
            self.IcPaSock.send(data)            
            self.lock.release()
        except socket.timeout, msg:
            self.lock.release()
            #print msg  
            iex = IcePAPException(IcePAPException.TIMEOUT, "Connection Timeout",msg)
            raise iex
        except socket.error, msg:
            self.lock.release()
            #print msg
            iex = IcePAPException(IcePAPException.ERROR, "Error sending data to the Icepap",msg)
            raise iex   
    
    def disconnect(self):
        if self.DEBUG:
            print "disconnecting from icepap..."
        if (self.Status == CStatus.Disconnected):
            if self.DEBUG:
                print "I was already disconnected!..."
            return
        try:
            self.IcPaSock.close()
            self.closeLogFile()
            self.Status = CStatus.Disconnected
            self.connected = 0
        except:
            iex = IcePAPException(IcePAPException.ERROR, "Error disconnecting the Icepap")
            raise iex   
        
    def try_to_connect(self):
        self.IcPaSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.IcPaSock.settimeout( self.timeout )        
        NOLINGER = struct.pack('ii', 1, 0)
        self.IcPaSock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, NOLINGER)
        try:
            self.IcPaSock.connect((self.IcePAPhost, self.IcePAPport))
            if self.log_path:
                self.openLogFile()
            self.Status = CStatus.Connected
            self.connected = 1
            if self.DEBUG:
                print "Connected to %s with DEBUG"%self.IcePAPhost
        except socket.error, msg:
            iex = IcePAPException(IcePAPException.TIMEOUT, "Error connecting to the Icepap",msg)
            #raise iex
            if self.DEBUG:
                print "Socket error while trying to connect to %s"%self.IcePAPhost
        except:
            iex = IcePAPException(IcePAPException.ERROR, "Error creating log file")
            #raise iex
            if self.DEBUG:
                print "Some exception while trying to connect to %s"%self.IcePAPhost


    # THIS IS NOT USED ANY MORE...
    def connect_retry(self):
        #print "connection broken\n trying to reconnect for a short while..."
        self.IcPaSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.IcPaSock.settimeout( self.timeout )
        NOLINGER = struct.pack('ii', 1, 0)
        self.IcPaSock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, NOLINGER)
        nsec=1;
        while nsec<=256:
            #print "nsec is ", nsec, "\n"
            try:
                self.IcPaSock.connect((self.IcePAPhost, self.IcePAPport))
                #print "reconnected!"
                nsec=257
                self.connected=1
            except:
                if nsec<=128:
                    #print "sleeping for ", nsec, "seconds"
                    time.sleep(nsec)
                nsec<<=1
                #print "nsec after left shift is ", nsec, "\n"
        if nsec<>257:
            #print "you've got a new socket that is not yet connected\ntry connecting it later"
            self.connected=0

import socket
import struct
import errno
import time
import icepapdef
from IcePAP import *


class EthIcePAP(IcePAP):

    connected=0
    shouldReconnect = True

    def connect(self,shouldReconnect=True):
        #print "connecting"
        #print "MYLOG IS THIS"
        self.shouldReconnect = shouldReconnect
        if (self.Status == CStatus.Connected):
            return 0
        self.IcPaSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.IcPaSock.settimeout( self.timeout )
        #self.IcPaSock.settimeout( 0.001 )
        
        NOLINGER = struct.pack('ii', 1, 0)
        self.IcPaSock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, NOLINGER)
        
        try:
            self.IcPaSock.connect((self.IcePAPhost, self.IcePAPport))
            if self.log_path:
                self.openLogFile()
        except socket.error, msg:            
            iex = IcePAPException(IcePAPException.TIMEOUT, "Error connecting to the Icepap",msg)
            raise iex
        except:
            iex = IcePAPException(IcePAPException.ERROR, "Error creating log file")
            raise iex
        self.Status = CStatus.Connected
        #self.IcPaSock.settimeout( 0 )
        #print "should be connected"
        self.connected=1
        return 0
    
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
                    #print "-----------------------------> more receive"
                ################################################

            self.lock.release()
            message = message + "\t\t[ " + data + " ]"
            self.writeLog(message)
            return data
        except socket.timeout, msg:
            #print "socket TIME OUT"
            self.writeLog(message + " " + str(msg))  
            self.lock.release()
            if self.shouldReconnect:
                self.disconnect()   
                #print "Disconnected socket\n"
                self.connected=0
                self.connect_retry()
            iex = IcePAPException(IcePAPException.TIMEOUT, "Connection Timeout",msg)
            raise iex
        except socket.error, msg:
            a,b,c=sys.exc_info()
            e,f=b
            self.writeLog(message + " " + str(sys.exc_info()))
            self.lock.release()  
            #print msg
            #print "Unexpected error:", sys.exc_info()            
            if e==errno.ECONNRESET or e==errno.EPIPE:
                if self.shouldReconnect:
                    self.disconnect()   
                    #print "Disconnected socket\n"
                    self.connect_retry()
            else:
                iex = IcePAPException(IcePAPException.ERROR, "Error sending command to the Icepap",msg)
                raise iex          
        

    
    def sendWriteCommand(self, cmd):
        if not self.connected:
            raise IcePAPException(IcePAPException.ERROR, "Connection error","no connection with the Icepap sytem")
        try:
            message = cmd
            cmd = cmd + "\n"
            self.lock.acquire()
            self.IcPaSock.send(cmd)
            self.writeLog(message)
            self.lock.release()
        except socket.timeout, msg:
            self.writeLog(message + " " + msg)      
            self.lock.release()           
            iex = IcePAPException(IcePAPException.TIMEOUT, "Connection Timeout",msg)
            raise iex            
        except socket.error, msg:
            self.writeLog(message + " " + str(sys.exc_info()))
            self.lock.release()  
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
        #print "Disconnecting ..."
        if (self.Status == CStatus.Disconnected):
            return 0
        try:
            self.IcPaSock.close()
            self.closeLogFile()
            self.Status = CStatus.Disconnected
            return 0
        except:
            iex = IcePAPException(IcePAPException.ERROR, "Error disconnecting the Icepap")
            raise iex   
        
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

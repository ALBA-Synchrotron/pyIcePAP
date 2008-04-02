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
            #print "lock acquired, socket sending"
            #MEANWHILE WORKAROUND
            # AS IT IS SAID IN http://www.amk.ca/python/howto/sockets/
            # SECTION "3 Using a Socket"
            # WE SHOULD WAIT UNTIL THE TERMINATOR CHAR '$' IS FOUND
            # OR SOME OTHER BETTER APPROACH
            #if cmd.count("CFGINFO") > 0:
            #    time.sleep(0.2)
            data = self.IcPaSock.recv(size)
            #print "Length of data string received is: ", data.__len__()
            #receive_result = self.IcPaSock.recv_into(data,<n0_bytes>,[<flags>)] (???)
            self.lock.release()
            message = message + "\t\t[ " + data + " ]"
            self.writeLog(message)
            return data
        except socket.timeout, msg:
            #print "socket TIME OUT"
            self.writeLog(message + " " + str(msg))  
            self.lock.release()
            self.disconnect()   
            #print "Disconnected socket\n"
            self.connected=0
            if self.shouldReconnect:
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
                self.disconnect()
                #print "Disconnected socket"
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

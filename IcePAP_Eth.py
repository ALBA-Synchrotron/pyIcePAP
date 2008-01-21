import socket
import struct
from IcePAP import *
import time
from errno import EWOULDBLOCK
import icepapdef

class EthIcePAP(IcePAP):

    def connect(self):
        #print "connecting"
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
            iex = IcePAPException(IcePAPException.TIMEOUT, "Error connecting to the Icepap")
            raise iex
        except:
            iex = IcePAPException(IcePAPException.ERROR, "Error creating log file")
            raise iex
        self.Status = CStatus.Connected
        #self.IcPaSock.settimeout( 0 )
        #print "connected"
        return 0
    
    def sendWriteReadCommand(self, cmd, size = 8192):
        try:
            message = cmd
            cmd = cmd + "\n"
            self.lock.acquire()
            self.IcPaSock.send(cmd)          
            data = self.IcPaSock.recv(size)
            message = message + "\t\t[ " + data + " ]"
            self.writeLog(message)
            self.lock.release()                      
            return data
        except socket.timeout, msg:
            self.writeLog(message + " " + str(msg))  
            self.disconnect()   
            self.lock.release()              
            iex = IcePAPException(IcePAPException.TIMEOUT, "Connection Timeout")
            raise iex
        except socket.error, msg:
            self.writeLog(message + " " + str(sys.exc_info()))
            self.lock.release()  
            print msg
            print "Unexpected error:", sys.exc_info()            
            iex = IcePAPException(IcePAPException.ERROR, "Error sending command to the Icepap")
            raise iex          
        

    
    def sendWriteCommand(self, cmd):
        try:
            message = cmd
            cmd = cmd + "\n"
            self.lock.acquire()
            self.IcPaSock.send(cmd)
            self.writeLog(message)
            self.lock.release()
        except socket.timeout, msg:
            self.disconnect()
            self.writeLog(message + " " + msg)      
            self.lock.release()           
            iex = IcePAPException(IcePAPException.TIMEOUT, "Connection Timeout")
            raise iex            
        except socket.error, msg:
            self.writeLog(message + " " + sys.exc_info())
            self.lock.release()  
            print "Unexpected error:", sys.exc_info()
            iex = IcePAPException(IcePAPException.ERROR, "Error sending command to the Icepap")
            raise iex   
            
        
    def sendData(self, data):
        try:
            self.lock.acquire()
            self.IcPaSock.send(data)            
            self.lock.release()
        except socket.timeout, msg:
            self.lock.release()
            print msg  
            self.disconnect()          
            iex = IcePAPException(IcePAPException.TIMEOUT, "Connection Timeout")
            raise iex
        except socket.error, msg:
            self.lock.release()
            print msg
            iex = IcePAPException(IcePAPException.ERROR, "Error sending data to the Icepap")
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
        
  


import sys
import IPython
from pyIcePAP import *

ice = None
def main():
    ip = IPython.ipapi.get()
    def connect(self,parameter_s='',name="connect"):
        split = parameter_s.split()
        host = split[0]
        port = 5000
        if len(split) == 2:
            port = split[1]
        self.ice = EthIcePAP(host,port)
        self.ice.connect(shouldReconnect=False)
    ip.expose_magic("connect",connect)

    def w(self,parameter_s='',name="cmd"):
        command = parameter_s.upper()
        command = command.replace("\\","")
        print "-> "+command
        try:
            self.ice.sendWriteCommand(command)
        except IcePAPException,e:
            print "!<- Some exception occurred: ",e
    ip.expose_magic("w",w)

    def wr(self,parameter_s='',name="cmd"):
        command = parameter_s.upper()
        command = command.replace("\\","")
        print "-> "+command
        try:
            #print "<- "+self.ice.sendWriteReadCommand(command)
            ans = self.ice.sendWriteReadCommand(command)
            return ans
        except IcePAPException,e:
            return e
    ip.expose_magic("wr",wr)

main()

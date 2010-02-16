import sys
import array
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
        self.ice.connect()
    ip.expose_magic("connect",connect)

    def disconnect(self,parameter_s='',name="disconnect"):
        self.ice.disconnect()
        self.ice = None
    ip.expose_magic("disconnect",disconnect)

    def w(self,parameter_s='',name="w"):
        command = parameter_s.upper()
        command = command.replace("\\","")
        print "-> "+command
        try:
            self.ice.sendWriteCommand(command)
        except Exception,e:
            print "!<- Some exception occurred: ",e
            return e
    ip.expose_magic("w",w)

    def wro(self,parameter_s='',name="wro"):
        command = parameter_s.upper()
        command = command.replace("\\","")
        print "-> "+command
        try:
            ans = self.ice.sendWriteReadCommand(command)
            return ans
        except Exception,e:
            print "!<- Some exception occurred: ",e
            return e
    ip.expose_magic("wro",wro)

    def wr(self,parameter_s='',name="wr"):
        print wro(self,parameter_s)
    ip.expose_magic("wr",wr)


    def sendfw(self,parameter_s='',name="sendfw"):
        try:
            filename = parameter_s
            f = file(filename,'rb')
            data = f.read()
            data = array.array('H',data)
            f.close()
            nworddata = (len(data))
            chksum = sum(data)
            print "File size: %d bytes, cheksum %d (%s)" % (len(data),chksum,hex(chksum))

            print "Setting MODE PROG"
            cmd = "#MODE PROG"
            answer = self.ice.sendWriteReadCommand(cmd)
            print answer
        
            print "Transferring firmware"
            cmd = "*PROG SAVE"
            self.ice.sendWriteCommand(cmd)
            
            startmark = 0xa5aa555a
            maskedchksum = chksum & 0xffffffff
            # BUGFIX FOR 64-BIT MACHINES
            self.ice.sendData(struct.pack('L',startmark)[:4])
            self.ice.sendData(struct.pack('L',nworddata)[:4])
            self.ice.sendData(struct.pack('L',maskedchksum)[:4])
            
            self.ice.sendData(data.tostring())
            time.sleep(7)
            print "Remember Icepap system is in MODE PROG"
            print self.ice.sendWriteReadCommand("?MODE")
        except Exception,e:
            print "!<- Some exception occurred: ",e
            return e
    ip.expose_magic("sendfw",sendfw)


    def listversions(self,parameter_s='',name="listversions"):
        versions_dict = {}
        ver_cmd = "VER"
        if parameter_s != '':
            ver_cmd = parameter_s.upper()
        sys_status = self.ice.sendWriteReadCommand("?SYSSTAT")
        sys_status = sys_status[sys_status.index("0x"):]
        sys_status = int(sys_status,16)
        for rack in range(16):
            if (sys_status & (1<<rack)) > 0:
                version = self.ice.sendWriteReadCommand("%d:?%s"%(rack*10,ver_cmd))
                versions_dict[rack*10] = version
                rack_status = self.ice.sendWriteReadCommand("?SYSSTAT %d"%rack)
                rack_status = rack_status[rack_status.index("0x"):]
                rack_status = int(rack_status.split(" ")[1],16)
                for driver in range(8):
                    if(rack_status & (1<<driver)) > 0:
                        addr = (rack*10+driver+1)
                        version = self.ice.sendWriteReadCommand("%d:?%s"%(addr,ver_cmd))
                        versions_dict[addr] = version
        return versions_dict
    ip.expose_magic("listversions",listversions)


main()

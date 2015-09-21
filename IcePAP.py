# PyIcepap for Icepap firmware version 1.16
try: import serial
except: pass

import sys
import re
from threading import Lock
import array
import struct
import numpy
import time, datetime
import operator

from icepapdef import IcepapStatus
from icepapdef import IcepapInfo
from icepapdef import IcepapRegisters

class CStatus:
    Disconnected, Connected, Error = range(3)
            
class IcePAPException(Exception):
    ERROR, TIMEOUT, CMD = range(3)
    def __init__(self, code, name, msg=""):
        self.code = code
        self.name = name
        self.msg = msg

    def __str__(self):
        string = "IcePAPException("+str(self.code)+","+str(self.name)+","+str(self.msg)+")"
        return string

    def __repr__(self):
        return self.__str__()


class IcePAP:    
    
    def __init__(self, host, port, timeout = 3, log_path = None):
        #print "IcePAP object created"
        self.IcePAPhost = host
        self.IcePAPport = int(port)
        self.Status = CStatus.Disconnected
        self.timeout = timeout
        self.lock = Lock()
        self.log_path = log_path
        self.log_file = None

        # THANKS TO VR FOR THE HINT...
        self.version_keys = ['CONTROLLER','DSP','FPGA','MCPU1','MCPU0','MCPU2','DRIVER']
        self.version_reg_exp = re.compile("(%s)\s*:\s*(\d+\.\d+)" % "|".join(self.version_keys),re.VERBOSE)

    
    def openLogFile(self):
        name = self.log_path+"/" + self.IcePAPhost + "."+datetime.datetime.now().strftime("%Y%m%d.%H%M%S")
        self.log_file = open(name, "w")
    
    def closeLogFile(self):
        if self.log_file:
            self.log_file.close()
        
    def writeLog(self, message):
        if self.log_file:
            prompt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ">\t"
            self.log_file.write(prompt+message+"\n")        

    # ------------ Interface Commands ------------------------------

    def connect(self):
        pass
    
    def sendWriteReadCommand(self, addr, command):
        pass
    
    def sendWriteCommand(self, addr, command):
        pass
    
    def sendData(self, data):
        pass
    
    def disconnect(self):
        pass

    ################################# BOARD COMMANDS ###########################################

    # ------------ Board Configuration and Identifaction Commands ------------------------------

    def getActive(self, addr):
        command = "%d:?ACTIVE" % addr
        ans = self.sendWriteReadCommand(command)
        return self.parseResponse(command, ans)
    
    def getMode(self, addr):
        command = "%d:?MODE" % addr
        ans = self.sendWriteReadCommand(command)
        return self.parseResponse(command, ans)

    def setMode(self, addr, mode):
        command = "%d:MODE %s" % (addr, mode)
        self.sendWriteCommand(command)

    def getStatusFromBoard(self, addr):
        command = "%d:?STATUS" % addr
        ans = self.sendWriteReadCommand(command)
        return self.parseResponse(command, ans)
    
    def getStatus(self, addr):
	    # 20140409 - BUG WITH ?_FSTATUS
	    # NOT CLEAR WHY TO USE _FSTATUS AND ALSO
	    # IT HAD A BUG IN PCBL2901 REPORTING DIFFERENT STATUS CODES
        #command = "?_FSTATUS %d" % addr
        #ans = self.sendWriteReadCommand(command)
        #if not 'ERROR' in ans:
        #    return self.parseResponse('?_FSTATUS', ans)
        # OLD MCPUs do not support ?_FSTATUS
        command = "?FSTATUS %d" % addr
        ans = self.sendWriteReadCommand(command)
        return self.parseResponse('?FSTATUS', ans)
    
    def getMultipleStatus(self, axis_list):
        axis = ""
        for addr in axis_list:
            axis = axis + str(addr) + " " 
        command = "?FSTATUS %s" % axis
        ans = self.sendWriteReadCommand(command)
        ans = self.parseResponse('?FSTATUS', ans)
        ans = ans.split()
        status_values = []
        i = 0
        for addr in axis_list:
            status_values.append((addr, ans[i]))
            i = i + 1
        return status_values     

    def getVStatus(self, addr):
        command = "%d:?VSTATUS" % addr
        ans = self.sendWriteReadCommand(command)
        return self.parseResponse(command, ans)
    
    def startConfig(self, addr):
        iex = IcePAPException(IcePAPException.ERROR,"Deprecated function 'start_config'", "use 'setConfig'")
        raise iex
        
    def setConfig(self, addr):
        command = "%d:CONFIG" % addr
        self.sendWriteCommand(command)
        
    def signConfig(self, addr, signature):
        command = "%d:CONFIG %s" % (addr, signature)
        self.sendWriteCommand(command)
   
    def getConfigSignature(self, addr):
        iex = IcePAPException(IcePAPException.ERROR,"Deprecated function 'getConfigSignature'", "use 'getConfig'")
        raise iex

    def getConfig(self,addr):
        command = "%d:?CONFIG" % addr
        ans = self.sendWriteReadCommand(command)
        return self.parseResponse(command, ans)
    
    def getCfg(self,addr):
        command = "%d:?CFG" % (addr)
        ans = self.sendWriteReadCommand(command)
        return self.parseResponse(command, ans)

    def getCfgParameter(self, addr, parameter):
        command = "%d:?CFG %s" % (addr, parameter)
        ans = self.sendWriteReadCommand(command)
        return self.parseResponse(command, ans)
    
    def setCfgParameter(self, addr, parameter, value):
        command = "%d:CFG %s %s" % (addr, parameter, value)
        self.sendWriteCommand(command)
    
    def getCfgInfo(self,addr):
        command = "%d:?CFGINFO" % (addr)
        ans = self.sendWriteReadCommand(command)
        return self.parseResponse(command, ans)
        
    def getCfgInfoParam(self,addr,param):
        command = "%d:?CFGINFO %s" % (addr,param)
        ans = self.sendWriteReadCommand(command)
        return self.parseResponse(command, ans)
        
    def getVersion(self, addr, module):
        command = "%d:?VER %s" % (addr, module)
        ans = self.sendWriteReadCommand(command)
        return self.parseResponse("%d:?VER" % addr, ans)

    def getVersionDsp(self, addr):
        return self.getVersion(addr, "DSP")

    def getVersionInfoDict(self, addr):
        command = "%d:?VER INFO" % (addr)
        ans = self.sendWriteReadCommand(command)
        info = self.version_reg_exp.findall(ans)
        return dict(info)

    def getVersionSaved(self):
        controller_version = self.getVersion(0,'CONTROLLER')
        if controller_version < '1.16':
            return 'Not_Available'
        #command = "?VER SAVED DRIVER"
        command = "?VER SAVED"
        ans = self.sendWriteReadCommand(command)
        ans = ans[ans.find('DRIVER'):]
        ans = ans.split('\n')[0]
        ans = ans.split(':')[1]
        driver_saved = ans.replace(' ','')
        return driver_saved

    def getName(self, addr):
        command = "%d:?NAME" % addr
        # FIX BUG OF INVALID NAMES
        # THIS COULD HAPPEN WHEN RECEIVED FROM FACTORY
        try:
            ans = self.sendWriteReadCommand(command)
            #return self.parseResponse(command, ans)

            # Requested by the ESRF
            # http://wikiserv.esrf.fr/esl/index.php/IcePAP_pending
            # issue 020
            parsed_ans = self.parseResponse(command, ans)
            if parsed_ans.count('ERROR') > 0:
                parsed_ans = ''
            return parsed_ans
        except:
            return "NAME_WITH_NON-PRINTABLE_CHARS"
    
    def setName(self, addr, name):
        command = "%d:NAME %s" % (addr, name)
        self.sendWriteCommand(command)

    def getId(self, addr):
        command = "%d:?ID HW" % addr
        ans = self.sendWriteReadCommand(command)
        return self.parseResponse("%d:?ID" % addr, ans)
    
    def getTime(self, addr):
        command = "%d:?TIME" % addr
        ans = self.sendWriteReadCommand(command)
        return self.parseResponse(command, ans)

    # ------------ Power and Motion control Commands ------------------------------      

    def getPower(self, addr):
        command = "%d:?POWER" % addr
        ans = self.sendWriteReadCommand(command)
        return self.parseResponse(command, ans)
    
    def setPower(self, addr, value):
        command = "%d:POWER %s" % (addr, value)
        self.sendWriteCommand(command)
    
    def getAuxPS(self, addr):
        command = "%d:?AUXPS" % addr
        ans = self.sendWriteReadCommand(command)
        return self.parseResponse(command, ans)
    
    def setAuxPS(self, addr, value):
        command = "%d:AUXPS %s" % (addr, value)
        self.sendWriteCommand(command)
        
    def getCSWITCH(self, addr):
        command = "%d:?CSWITCH" % addr
        ans = self.sendWriteReadCommand(command)
        return self.parseResponse(command, ans)
    
    def setCSWITCH(self, addr, value):
        command = "%d:CSWITCH %s" % (addr, value)
        self.sendWriteCommand(command)
        
    def getPositionFromBoard(self, addr, pos_sel = "AXIS"):
        command = "%d:?POS %s" % (addr, pos_sel)
        ans = self.sendWriteReadCommand(command)
        return self.parseResponse("%d:?POS" % addr, ans)
    
    def getPosition(self, addr):
        command = "?_FPOS %d" % addr
        ans = self.sendWriteReadCommand(command)
        if not 'ERROR' in ans:
            return self.parseResponse('?_FPOS', ans)
        # OLD MCPUs do not support ?_FPOS
        command = "?FPOS %d" % addr
        ans = self.sendWriteReadCommand(command)
        return self.parseResponse('?FPOS', ans)
    
    def getMultiplePositionFromBoard(self, axis_list):
        axis = ""
        for addr in axis_list:
            axis = axis + str(addr) + " " 
        command = "?POS %s" % axis
        ans = self.sendWriteReadCommand(command)
        ans = self.parseResponse('?POS', ans)
        ans = ans.split()
        position_values = []
        i = 0
        for addr in axis_list:
            position_values.append((addr, ans[i]))
            i = i + 1
        return position_values
                
    def getMultiplePosition(self, axis_list):
        axis = ""
        for addr in axis_list:
            axis = axis + str(addr) + " " 
        command = "?FPOS %s" % axis
        ans = self.sendWriteReadCommand(command)
        ans = self.parseResponse('?FPOS', ans)
        ans = ans.split()
        position_values = []
        i = 0
        for addr in axis_list:
            position_values.append((addr, ans[i]))
            i = i + 1
        return position_values     
                
    def setPosition(self, addr, pos_val, pos_sel = "AXIS"):
        command = "%d:POS %s %d" % (addr, pos_sel, pos_val)
        self.sendWriteCommand(command)
    
    def getEncoder(self, addr, pos_sel = "AXIS"):
        command = "%d:?ENC %s" % (addr, pos_sel)
        ans = self.sendWriteReadCommand(command)
        return self.parseResponse("%d:?ENC" % addr, ans)
    
    def setEncoder(self, addr, pos_val, pos_sel = "AXIS"):
        command = "%d:ENC %s %d" % (addr, pos_sel, pos_val)
        self.sendWriteCommand(command)
    
    def getSpeed(self, addr):
        command = "%d:?VELOCITY" % addr
        ans = self.sendWriteReadCommand(command)
        return self.parseResponse(command, ans)
        
    def setSpeed(self, addr, speed):
        command = "%d:VELOCITY %s" % (addr, speed)
        self.sendWriteCommand(command)
    
    def getAcceleration(self, addr):
        command = "%d:?ACCTIME" % addr
        ans = self.sendWriteReadCommand(command)
        return self.parseResponse(command, ans)
        
    def setAcceleration(self, addr, acctime):
        command = "%d:ACCTIME %s" % (addr, acctime)
        self.sendWriteCommand(command)
    
    def move(self, addr, abs_pos):
        command = "%d:MOVE %d " % (addr, abs_pos)
        self.sendWriteCommand(command)                
           
    def rmove(self, addr, steps):
        command = "%d:RMOVE %d " % (addr, steps)
        self.sendWriteCommand(command)
    
    def move_in_config(self, addr, steps):
        iex = IcePAPException(IcePAPException.ERROR,"Deprecated function 'move_in_config'", "use 'cmove'")
        raise iex

    def cmove(self, addr, steps):
        command = "%d:CMOVE %d " % (addr, steps)
        self.sendWriteCommand(command)
    
    def jog(self, addr, speed):
        self.sendWriteCommand("%d:JOG %d" % (addr, speed))

    def cjog(self, addr, speed):
        self.sendWriteCommand("%d:CJOG %d" % (addr, speed))

    def stopMotor(self, addr):
        iex = IcePAPException(IcePAPException.ERROR,"Deprecated function 'stopMotor'", "use 'stop'")
        raise iex

    def stop(self, addr):
        command = "%d:STOP" % addr
        self.sendWriteCommand(command)

    def abortMotor(self, addr):
        iex = IcePAPException(IcePAPException.ERROR,"Deprecated function 'abortMotor'", "use 'abort'")
        raise iex

    def abort(self, addr):
        command = "%d:ABORT" % addr
        self.sendWriteCommand(command)

    # ------------- Closed Loop commands ------------------------
    def getClosedLoop(self,addr):
        command = "%d:?PCLOOP" % addr
        ans = self.sendWriteReadCommand(command)
        return self.parseResponse(command,ans)

    def setClosedLoop(self,addr,enc):
        command = "%d:PCLOOP %s" % (addr,enc)
        self.sendWriteCommand(command)

    def syncEncoders(self, addr):
        command = "%d:ESYNC" % addr
        self.sendWriteCommand(command)

    # ------------- Input/Output commands ------------------------
    def getIndexerSource(self, addr):
        iex = IcePAPException(IcePAPException.ERROR,"Deprecated function 'getIndexerSource'", "use 'getIndexer'")
        raise iex

    def getIndexer(self, addr):
        command = "%d:?INDEXER" % addr
        ans = self.sendWriteReadCommand(command)
        return self.parseResponse(command, ans)
    
    def setIndexerSource(self, addr, src):
        iex = IcePAPException(IcePAPException.ERROR,"Deprecated function 'setIndexerSource'", "use 'setIndexer'")
        raise iex

    def setIndexer(self, addr, src):
        command = "%d:INDEXER %s" % (addr, src)
        self.sendWriteCommand(command)
        
    def getInfoSource(self, addr, info):
        iex = IcePAPException(IcePAPException.ERROR,"Deprecated function 'getInfoSource'", "use 'getInfo'")
        raise iex

    def getInfo(self, addr, info):
        command = "%d:?%s" % (addr, info)
        ans = self.sendWriteReadCommand(command)
        return self.parseResponse(command, ans)
     
    def setInfoSource(self, addr, info, src, polarity="NORMAL"):
        iex = IcePAPException(IcePAPException.ERROR,"Deprecated function 'setInfoSource'", "use 'setInfo'")
        raise iex

    def setInfo(self, addr, info, src, polarity="NORMAL"):
        command = "%d:%s %s %s" % (addr, info, src, polarity)
        self.sendWriteCommand(command)


    # ------------- NEW FEATURES WITH VERSION 2.x ------------------
    def sendListDat(self, addr, position_list):
        l = position_list
        lushorts = struct.unpack('%dH' % (len(l) * 2), struct.pack('%df' % len(l), *l))

        cmd = "%d:*LISTDAT FLOAT" % addr
        self.sendWriteCommand(cmd, prepend_ack=False)

        startmark = 0xa5aa555a
        nworddata = (len(lushorts))
        checksum = sum(lushorts)
        maskedchksum = checksum & 0xffffffff

        self.sendData(struct.pack('L',startmark)[:4])
        self.sendData(struct.pack('L',nworddata)[:4])
        self.sendData(struct.pack('L',maskedchksum)[:4])

        data = array.array('H', lushorts)
        self.sendData(data.tostring())

    def sendEcamDatIntervals(self, addr, start_pos, end_pos, intervals, source='AXIS'):
        cmd = ('%d:ECAMDAT %s %d %d %d' 
                % (addr, source, start_pos, end_pos, intervals))
        self.sendWriteCommand(cmd)
        
    def sendEcamDat(self, addr, source='AXIS', signal='PULSE', position_list=[0,1,2,3,4,5,6,7,8,9]):
        signal = signal.upper()
        if signal not in IcepapInfo.EcamSignals:
            iex = IcePAPException(IcePAPException.ERROR, "Error sending ECAMDAT LIST",
                                  "Signal not in %s" % str(IcepapInfo.EcamSignals))
            raise iex
        
        source = source.upper()
        if source not in IcepapRegisters.EcamSourceRegisters:
            iex = IcePAPException(IcePAPException.ERROR, "Error sending ECAMDAT LIST",
                                  "Source (%s) not in %s" % (source, str(IcepapRegisters.EcamSourceRegisters)))
            raise iex

        l = position_list
        lushorts = struct.unpack('%dH' % (len(l) * 2), struct.pack('%df' % len(l), *l))

        cmd = "%d:*ECAMDAT %s FLOAT" % (addr, source)
        self.sendWriteCommand(cmd, prepend_ack=False)

        startmark = 0xa5aa555a
        nworddata = (len(lushorts))
        checksum = sum(lushorts)
        maskedchksum = checksum & 0xffffffff

        self.sendData(struct.pack('L',startmark)[:4])
        self.sendData(struct.pack('L',nworddata)[:4])
        self.sendData(struct.pack('L',maskedchksum)[:4])

        data = array.array('H', lushorts)
        self.sendData(data.tostring())

        cmd = '%d:ECAM %s' % (addr, signal)
        self.sendWriteCommand(cmd)
        
        
    # ------------- Help and error commands ------------------------
    def blink(self, addr, secs):
        command = "%d:BLINK %d" % (addr,secs)
        self.sendWriteCommand(command)

    ################################# SYSTEM COMMANDS ###########################################

    def getSysStatus(self):
        command = "?SYSSTAT"
        ans = self.sendWriteReadCommand(command)
        return self.parseResponse(command, ans)
   
    def getRackStatus(self, racknr):
        command = "?SYSSTAT %d" % racknr
        ans = self.sendWriteReadCommand(command)
        ans = self.parseResponse("?SYSSTAT", ans)
        return ans.split()

    def getSystemVersion(self):
        return self.getVersion(0, "")
    
    def resetSystem(self):
        self.sendWriteCommand("RESET")

    def getMultiplePositions(self, axis_list):
        axis = ""
        for addr in axis_list:
            axis = axis + str(addr) + " " 
        command = "F?POS %s" % axis
        ans = self.sendWriteReadCommand(command)
        ans = self.parseResponse("?POS", ans)
        ans = ans.split()
        pos_values = []
        i = 0
        for addr in axis_list:
            pos_values.append([addr, ans[i]])
            i = i + 1
        return pos_values     
        
    def setMultiplePosition(self, pos_val_list, pos_sel = "AXIS"):
        values = ""
        for addr, value in pos_val_list:
            values = values + str(addr) + " " + str(value) + " "
        command = "POS %s %s" % (pos_sel, values)
        self.sendWriteCommand(command)
    
    def getMultipleEncoder(self, axis_list, pos_sel = "AXIS"):
        axis = ""
        for addr in axis_list:
            axis = axis + str(addr) + " " 
        command = "?ENC %s %s" % (pos_sel, axis)
        ans = self.sendWriteReadCommand(command)
        ans = self.parseResponse("?ENC", ans)
        ans = ans.split()
        pos_values = []
        i = 0
        for addr in axis_list:
            pos_values.append([addr, ans[i]])
            i = i + 1
        return pos_values
    
    def setMultipleEncoder(self, pos_val_list, pos_sel = "AXIS"):
        values = ""
        for addr, value in pos_val_list:
            values = values + str(addr) + " " + str(value) + " "
        command = "ENC %s %s" % (pos_sel, values)
        self.sendWriteCommand(command)
    
    def getMultipleSpeeds(self, axis_list):
        axis = ""
        for addr in axis_list:
            axis = axis + str(addr) + " " 
        command = "?VELOCITY %s" % axis
        ans = self.sendWriteReadCommand(command)
        ans = self.parseResponse("?VELOCITY", ans)
        ans = ans.split()
        values = []
        i = 0
        for addr in axis_list:
            values.append([addr, ans[i]])
            i = i + 1
        return values 
        
    def setMultipleSpeeds(self, val_list):
        values = ""
        for addr, value in val_list:
            values = values + str(addr) + " " + str(value) + " "
        command = "VELOCITY %s" % values
        self.sendWriteCommand(command)
    
    def getMultipleAccelerations(self, axis_list):
        axis = ""
        for addr in axis_list:
            axis = axis + str(addr) + " " 
        command = "?ACCTIME %s" % axis
        ans = self.sendWriteReadCommand(command)
        ans = self.parseResponse("?ACCTIME", ans)
        ans = ans.split()
        values = []
        i = 0
        for addr in axis_list:
            values.append([addr, ans[i]])
            i = i + 1
        return values 
        
    def setMultipleAccelerations(self, val_list):
        values = ""
        for addr, value in val_list:
            values = values + str(addr) + " " + str(value) + " "
        command = "ACCTIME %s" % values
        self.sendWriteCommand(command)
    
    def moveMultiple(self, val_list):
        values = ""
        for addr, value in val_list:
            values = values + str(addr) + " " + str(value) + " "
        command = "MOVE %s " % values
        self.sendWriteCommand(command)
    
    def moveMultipleGrouped(self, val_list):
        values = ""
        for addr, value in val_list:
            values = values + str(addr) + " " + str(value) + " "
        command = "MOVE GROUP %s " % values
        self.sendWriteCommand(command)
    
    def rmoveMultiple(self, val_list):
        values = ""
        for addr, value in val_list:
            values = values + str(addr) + " " + str(value) + " "
        command = "RMOVE %s " % values
        self.sendWriteCommand(command)
    
    def stopMultipleMotor(self, axis_list):
        axis = ""
        for addr in axis_list:
            axis = axis + str(addr) + " " 
        command = "STOP %s" % axis
        self.sendWriteCommand(command)

    def abortMultipleMotor(self, axis_list):
        axis = ""
        for addr in axis_list:
            axis = axis + str(addr) + " " 
        command = "ABORT %s" % axis
        self.sendWriteCommand(command)



    ############################################################################################
    ############################################################################################


    def setDefaultConfig(self,addr):
        command = "%d:_CFG DEFAULT" % addr
        self.sendWriteCommand(command)

    def getCurrent(self, addr):
        return self.getCfgParameter(addr, "NCURR")
    
    def readParameter(self, addr, name, args = ""):
        command = "%d:?%s %s" % (addr, name, args)
        ans = self.sendWriteReadCommand(command)
        return self.parseResponse("%d:?%s" % (addr, name) , ans)
        
    def writeParameter(self, addr, name, value):
        command = "%d:%s %s" % (addr, name, value)
        self.sendWriteCommand(command)
        
    def isExpertFlagSet(self,addr):
        try:
            return self.getCfgParameter(addr, "EXPERT")
        except:
            return "NO"

    def setExpertFlag(self,addr):
        command = "%d:CFG EXPERT" % (addr)
        self.sendWriteCommand(command)

    def disable(self, addr):
        self.setPower(addr, "OFF")
    
    def enable(self, addr):
        self.setPower(addr, "ON")

    def checkDriver(self, addr):
        ans = self.getId(addr)
        return 0
    
    def icepapfiforst(self):
        print ""
            
    def IceFindError(self,ice_answer):
        if (ice_answer.find("ERROR") != -1):
            return True
        else:
            return False
        
    def IceCheckError(self,ice_answer):
        if (ice_answer.find("ERROR") != -1):
            new_ans = self.sendWriteReadCommand(0, "?ERR 1")
            print new_ans + " in IceCheckError"
            return new_ans
        else:
            return "IcePAPError. Not Identified"

    def parseResponse(self, command, ans):
        command = command.upper()
        command_first_word = command.split(' ')[0]
        if ans.find(command) != -1:
            ans = ans.replace(command, "")
            ans = ans.lstrip()
            return ans
        elif ans.find(command_first_word) != -1 and ans.find('ERROR') == -1:
            # I'M IN ONE OF MULTIAXIS COMMANDS LIKE ?FSTATUS
            ans = ans.replace(command_first_word, '')
            ans = ans.lstrip()
            return ans
        else:
            iex = IcePAPException(IcePAPException.CMD, ans)
            raise iex


    ############################################################################################
    ############################################################################################

    # ------------- library utilities ------------------------

    def sendFirmware(self, filename, save=True):
        f = file(filename,'rb')
        data = f.read()
        data = array.array('H',data)
        f.close()
        nworddata = (len(data))
        chksum = sum(data)

        cmd = "*PROG"
        if save:
            cmd += ' SAVE'
        self.sendWriteCommand(cmd)
        
        startmark = 0xa5aa555a
        maskedchksum = chksum & 0xffffffff
        # BUGFIX FOR 64-BIT MACHINES
        self.sendData(struct.pack('L',startmark)[:4])
        self.sendData(struct.pack('L',nworddata)[:4])
        self.sendData(struct.pack('L',maskedchksum)[:4])
        
        self.sendData(data.tostring())

    
    # GET PROGRAMMING PROGRESS STATUS
    def getProgressStatus(self):
        # TRY FIRST THE NEW ?_PROG command
        command = "?_PROG"
        ans = self.sendWriteReadCommand(command)
        ans = self.parseResponse(command, ans)
        # IF ANY ERROR, TRY THE OLD ?PROG command
        if ans.count("ERROR") > 0:
            command = "?PROG"
            ans = self.sendWriteReadCommand(command)
            ans = self.parseResponse(command, ans)
        if ans.count("ACTIVE") > 0:
            p = int(ans.split(" ")[1].split(".")[0])
            return p
        if ans.count("DONE") > 0:
            return 'DONE'
        return None
        
    # GET RACKS ALIVE
    def getRacksAlive(self):
        racks = []
        rackMask = 0
        try:
            rackMask = int(self.getSysStatus(),16)
        except:
            pass
        for rack in range(16):
            if (rackMask & (1<<rack)) != 0:
                racks.append(rack)
        return racks

    # GET DRIVERS ALIVE
    def getDriversAlive(self):
        drivers = []
        rackMask = 0
        try:
            rackMask = int(self.getSysStatus(),16)
        except:
            pass
        for rack in range(16):
            if (rackMask & (1<<rack)) != 0:
                rackStatus = self.getRackStatus(rack)
                driverMask = int(rackStatus[1],16)
                for driver in range(8):
                    if (driverMask & (1<<driver)) != 0:
                        drivers.append((rack*10)+driver+1)
        return drivers

    # ISG HOMING TEMPORARY FUNCTIONS
    def isg_cfghome(self,addr,signal,edge):
        command = "%d:ISG CFGHOME %d %d" % (addr,signal,edge)
        # THIS IS FOR THE BUG IN THE ICEPAP FIRMWARE...
        self.sendWriteCommand(command)
        self.sendWriteCommand(command)

    def isg_homecfgd(self,addr):
        command = "%d:?ISG ?HOMECFGD" % (addr)
        ans = self.sendWriteReadCommand(command)
        return self.parseResponse("%d:?ISG"%addr, ans)

    def isg_homed(self,addr):
        command = "%d:?ISG ?HOMED" % (addr)
        ans = self.sendWriteReadCommand(command)
        return '1' ==  self.parseResponse("%d:?ISG"%addr, ans)
        
    def isg_switches(self,addr,switch=None):
        command = "%d:?ISG ?SW" % (addr)
        ans = self.sendWriteReadCommand(command)
        ans = self.parseResponse("%d:?ISG"%addr, ans)
        switches = ans.split()
        if switch is None:
            return [int(switches[0]),int(switches[1]),int(switches[2])]
        else:
            return int(switches[switch])

    def isg_sw_lim_neg(self,addr):
        return self.isg_switches(addr,0) == 1
        
    def isg_sw_lim_pos(self,addr):
        return self.isg_switches(addr,1) == 1
        
    def isg_sw_home(self,addr):
        return self.isg_switches(addr,2) == 1

    # ISG POWER INFO
    def isg_powerinfo(self,addr):
        command = "%d:?ISG ?PWRINFO" % (addr)
        ans = self.sendWriteReadCommand(command)
        return self.parseResponse("%d:?ISG"%addr, ans)
   
    # JLIDON COMMANDS FOR TESTING THE BOARDS
    # 02/09/2009
    def getMeas(self, addr, meas_sel = "I"):
        command = "%d:?MEAS %s" % (addr, meas_sel)
        ans = self.sendWriteReadCommand(command)
        return self.parseResponse("%d:?MEAS" % addr, ans)

    def getTOvl(self, addr, pos_sel = "ovl"):
        command = "%d:?_T_CMD %s" % (addr, pos_sel)
        ans = self.sendWriteReadCommand(command)
        return self.parseResponse("%d:?_T_CMD" % addr, ans)

    def setTOvl(self, addr, pos_val, pos_sel = "ovl"):
        command = "%d:_T_CMD %s %d" % (addr, pos_sel, pos_val)
        self.sendWriteCommand(command)

    def setDC(self, addr, dc_val, dc_sel = "dcsd"):
        command = "%d:_T_CMD %s %d" % (addr, dc_sel, dc_val)
        self.sendWriteCommand(command)

    def getTSD(self, addr):
        return self.getMeas(addr, "VM")

    def setTSD(self, addr, pos_val):
        self.setDC(addr, dc_val, "DCSD")

    def getTVA(self, addr):
        return self.getMeas(addr, "IA")

    def setTVA(self, addr, pos_val):
        self.setDC(addr, dc_val, "DCA")

    def getTVB(self, addr):
        return self.getMeas(addr, "IB")

    def setTVB(self, addr, pos_val, pos_sel = "dcb"):
        self.setDC(addr, dc_val, "DCB")

    def getTVCC(self, addr):
        return self.getMeas(addr, "VCC")

    # GCUNI MORE INFO REGARDING THE STATUS REGISTER
    # XX/03/2010
    def getDecodedStatus(self, addr):
        status = self.getStatus(addr)
        return self.decodeStatus(status)

    def decodeStatus(self, status):
        if not isinstance(status, int):
            if isinstance(status, str):
                status = int(status, 16)
            else:
                return None

        status_dict = {}
        for key in IcepapStatus.status_keys:
            value = None
            if key == 'present':
                value = IcepapStatus.isPresent(status)
            elif key == 'alive':
                value = IcepapStatus.isAlive(status)
            elif key == 'mode':
                value = IcepapStatus.getMode(status)
            elif key == 'disable':
                value = IcepapStatus.isDisabled(status)
            elif key == 'indexer':
                value = IcepapStatus.getIndexer(status)
            elif key == 'ready':
                value = IcepapStatus.isReady(status)
            elif key == 'moving':
                value = IcepapStatus.isMoving(status)
            elif key == 'settling':
                value = IcepapStatus.isSettling(status)
            elif key == 'outofwin':
                value = IcepapStatus.isOutOfWin(status)
            elif key == 'warning':
                value = IcepapStatus.isWarning(status)
            elif key == 'stopcode':
                value = IcepapStatus.getStopCode(status)
            elif key == 'lim+':
                value = IcepapStatus.getLimitPositive(status)
            elif key == 'lim-':
                value = IcepapStatus.getLimitNegative(status)
            elif key == 'home':
                value = IcepapStatus.inHome(status)
            elif key == '5vpower':
                value = IcepapStatus.is5VPower(status)
            elif key == 'verserr':
                value = IcepapStatus.isVersErr(status)
            elif key == 'poweron':
                value = IcepapStatus.isPowerOn(status)
            elif key == 'info':
                value = IcepapStatus.getInfo(status)
            meaning = IcepapStatus.status_meaning[key].get(value, 'Info field => in OPER, master index; in PROG, prog phase')
            status_dict[key] = (value, meaning)
        return status_dict

    # JLIDON - DEBUG INTERNALS
    # 23/04/2010

    def serr(self, addr):
        command = '%d:?SERR' % (addr)
        ans = self.sendWriteReadCommand(command)
        return self.parseResponse(command, ans)

    def memory(self, addr):
        command = '%d:?MEMORY' % (addr)
        ans = self.sendWriteReadCommand(command)
        return self.parseResponse(command, ans)

    def warning(self, addr):
        command = '%d:?WARNING' % (addr)
        ans = self.sendWriteReadCommand(command)
        return self.parseResponse(command, ans)

    def alarm(self, addr):
        command = '%d:?ALARM' % (addr)
        ans = self.sendWriteReadCommand(command)
        return self.parseResponse(command, ans)

    def isg_settingsflags(self, addr):
        command = '%d:?ISG ?SETTINGSFLAGS' % (addr)
        ans = self.sendWriteReadCommand(command)
        return self.parseResponse('%d:?ISG'%addr, ans)

    def isg_dumpinternals(self, addr):
        command = '%d:?ISG ?DUMPINTERNALS' % (addr)
        ans = self.sendWriteReadCommand(command)
        return self.parseResponse('%d:?ISG'%addr, ans)

    def isg_dumpfpgareg(self, addr):
        command = '%d:?ISG ?DUMPFPGAREG' % (addr)
        ans = self.sendWriteReadCommand(command)
        return self.parseResponse('%d:?ISG'%addr, ans)

    def debug_internals(self, addr):
        sysstat = self.getSysStatus()
        name = self.getName(addr)
        now = datetime.datetime.now().strftime('%Y/%m/%d_%H:%M:%S')
        template = '=== ICEPAP INTERNALS %d@%s (%s) time: %s ===\n' % (addr, self.IcePAPhost, name, now)
        template += 'System Status: %s\n' % sysstat
        for rack in self.getRacksAlive():
            rack_status = self.getRackStatus(rack)
            template += 'Rack Status %d: %s\n' % (rack, rack_status)
        m_version = str(self.getVersionInfoDict(0))
        template += 'Master Firmware Version: %s\n' % m_version
        d_version = str(self.getVersionInfoDict(addr))
        template += 'Driver Firmware Version: %s\n' % d_version
        mode = self.getMode(addr)
        template += 'Driver Mode %d: %s\n' % (addr, mode)
        d_time = self.getTime(addr)
        template += 'Driver Time %d: %s\n' % (addr, d_time)
        addr_status = self.getStatusFromBoard(addr)
        template += 'Driver Status %d: %s\n' % (addr, addr_status)
        template += 'VStatus: ---------------------------------\n'
        vstatus = self.getVStatus(addr)
        template += vstatus
        #status_dict = self.decodeStatus(addr_status)
        #template += 'Decoded Status: --------------------------\n'
        #for key in IcepapStatus.status_keys:
        #    template += '%s: %s\n' %(key, status_dict[key])
        isg_powerinfo = self.isg_powerinfo(addr)
        template += 'Power Info: ------------------------------\n%s\n' % isg_powerinfo
        serr = self.serr(addr)
        template += 'System Errors: ---------------------------\n%s\n' % serr
        memory = self.memory(addr)
        template += 'Memory: ----------------------------------\n%s\n' % memory
        warning = self.warning(addr)
        template += 'Warning: ---------------------------------\n%s\n' % warning
        alarm = self.alarm(addr)
        template += 'Alarm: -----------------------------------\n%s\n' % alarm
        isg_settingsflags = self.isg_settingsflags(addr)
        template += 'Settings Flags: --------------------------\n%s\n' % isg_settingsflags
        isg_dumpinternals = self.isg_dumpinternals(addr)
        template += 'Dump Internals: --------------------------\n%s\n' % isg_dumpinternals
        isg_dumpfpgareg = self.isg_dumpfpgareg(addr)
        template += 'Dump FPGA reg: ---------------------------\n%s\n' % isg_dumpfpgareg
        template += ' =============================='

        return template


    # GCUNI - BL13
    # 17/07/2010
    # Detect if a motor is connected.
    # Put power, and measure the current 10 times
    # add it up and check that it is zero
    def motor_connected(self, addr):
        power_state = self.getPower(addr)
        self.enable(addr)
        sum_i = 0
        for i in range(100):
            sum_i += float(self.getMeas(addr, 'I'))
        # Restore power state
        self.setPower(addr, power_state)
        return (sum_i > 1)

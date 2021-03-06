import json
import logging
import random
import sys
import threading
import time
import traceback

from magi.util import database
from magi.util.agent import DispatchAgent, agentmethod
from magi.util.config import getNodeName

from bbb_iso_old import BBB_ISO
from client_comm_service import ClientCommService


log = logging.getLogger(__name__)

class ISOClientAgent(DispatchAgent):

    def __init__(self):
        DispatchAgent.__init__(self)
        self.server = None # configured by MAGI
        self.configFileName = None # configured by MAGI

    @agentmethod()
    def initClient(self, msg):
        log.info("Initializing client...")

        self.collection = database.getCollection(self.name)
        self.collection.remove()
        
        # nodeName: "clientnode-3" --> nodeIndex: 3
        self.nodeIndex = int(getNodeName().split("-")[1]) 

        with open(self.configFileName, 'r') as configFile:
            globalConfig = json.load(configFile)

        unitConfig = globalConfig["units"][self.nodeIndex-1]

        self.CID = unitConfig["CID"]
        self.unit = BBB_ISO.dictToUnit(unitConfig)
        self.unit.tS = globalConfig["timeStep"]
        self.t = 0

    @agentmethod()
    def registerWithServer(self, msg):
        log.info("Connecting to server...")
        self.comms = ClientCommService()
        self.cthread = self.comms.initAsClient(self.server, self.CID, self.replyHandler)
        # self.cthread = self.comms.initAsClient(toControlPlaneNodeName(self.server), self.CID, self.replyHandler)
        self.sendRegister()
        while self.comms.registered is False:
            time.sleep(0.1 + (random.random()*0.3))
        return True
        
    @agentmethod()
    def startClient(self, msg):
        log.info("Starting client's simulation...")
        self.running = 1
        self.runClient()
        return True

    @agentmethod()
    def stopClient(self, msg):
        """ No longer being used..."""
        log.info("Shutting client down...")
        # self.running = 0
        # time.sleep(0.1) # wait for thread to stop
        # self.deRegister()
        # time.sleep(0.1)  # wait for thread to stop
        # self.comms.running = 0
        # return True

    def runClient(self):
        try:
            while self.running:
                log.info("%s Running" % threading.currentThread().name)
                
                log.info("Unit updating itself...")
                self.unit.updateE(self.t)
                self.unit.updateAgility(self.t)
                self.unit.updatePForced()
                
                # #Adapt to constraints (change P value when constrained despite no comms)
                # if self.unit.pForced > self.unit.p:
                #     log.info("%s Unit forced to modify its own power, not dispatched enough" % threading.currentThread().name)         
                #     self.unit.setP(self.unit.pForced)

                self.logUnit()
                self.t += 1
                time.sleep(self.unit.tS/10.0)
        except Exception:
            log.info("Thread %s threw an exception during main loop" % threading.currentThread().name)
            exc_type, exc_value, exc_tb = sys.exc_info()
            log.error(''.join(traceback.format_exception(exc_type, exc_value, exc_tb)))
        finally:
            self.comms.stop()

    def logUnit(self):
        log.info("%s Logging/Saving unit stats to mongo" % threading.currentThread().name)
        stats = self.unit.__dict__.copy()
        if 'agent' in stats:
            log.info("key 'agent' removed from stats")
            del stats["agent"]
        if 'host' in stats:
            log.info("key 'host' removed from stats")
            del stats["host"]
        if 'created' in stats:
            log.info("key 'created' removed from stats")
            del stats["created"]
        
        stats["CID"] = self.CID
        self.collection.insert(stats)

    def updateUnit(self, t, p):
        log.info("%s updating unit" % threading.currentThread().name)
        self.unit.p = p
        self.unit.updateE(t)
        self.unit.updateAgility(t)
        self.unit.updatePForced()

    def replyHandler(self,CID,msg):
        log.info("%s in reply handler" % threading.currentThread().name)
        log.info("%s Received msg: %s" % (threading.currentThread().name, repr(msg)))

        mtype = msg["type"]
        payload = msg["payload"]
        if mtype == 'dispatch':
            newTime = payload["currentTime"]
            log.info("%s Updating Unit params based on dispatch" % threading.currentThread().name)
            self.updateUnit(newTime, payload["p"])
            self.t = newTime
            # self.sendEnergy() 
            # self.sendParams()
        elif mtype == 'exit':
            log.info("Exit message received from server")
            self.running = 0
        else:
            log.info("UNKNOWN MESSAGE TYPE RECEIVED")

        # do we want to return E here?

    def sendMsg(self, mtype, payload):
        msg = {}
        msg["type"] = mtype
        msg["payload"] = payload
        self.comms.clientSendValue(msg)

    def sendParams(self):
        payload=self.unit.paramsToDict()
        mtype='setParam'
        self.sendMsg(mtype,payload)
        
    def sendEnergy(self):
        payload={}
        payload["e"]=self.unit.e
        mtype='setEnergy'
        self.sendMsg(mtype,payload)

    def sendRegister(self):
        log.info("Registering with server!")
        payload = self.unit.paramsToDict()
        mtype = 'register'
        self.sendMsg(mtype,payload)

    def deRegister(self):
        payload='null'
        mtype='deregister'
        self.sendMsg(mtype,payload)
        

def getAgent(**kwargs):
    agent = ISOClientAgent()
    agent.setConfiguration(None, **kwargs)
    return agent

#!/usr/bin/env python

import logging
import sys

from magi.util import helpers
from magi.util.agent import DispatchAgent, agentmethod
from magi.util.processAgent import initializeProcessAgent
import yaml

from commClient import ClientCommService


log = logging.getLogger(__name__)

class Client(DispatchAgent):
    
    def __init__(self):
        # The default arguments for server and clientId go in here 
        DispatchAgent.__init__(self)
        self.server = 'localhost' 
        self.clientId = None 
    
    def setConfiguration(self, msg, **kwargs):
        DispatchAgent.setConfiguration(self, msg, **kwargs)
        
        from magi.testbed import testbed
        if self.clientId == None: 
            self.hostname = testbed.nodename
            log.info("Hostname: %s", self.hostname)
            self.clientId = self.hostname 

        # The clientId can be set programmatically to append the hostname .
        self.setClientid() 
        self.commClient = None
    
    @agentmethod()
    def startclient(self, msg):
        self.commClient = ClientCommService(self.clientId)
        self.commClient.initCommClient(self.server, self.requestHandler)
    
    @agentmethod()
    def stopclient(self, msg):
        DispatchAgent.stop(self, msg)
        if self.commClient:
            self.commClient.stop()
        
    def requestHandler(self, msgData):
        log.info("RequestHandler: %s", msgData)
        
        dst = msgData['dst']
        if dst != self.hostname:
            log.error("Message sent to incorrect destination.")
            return
        
        src= msgData['src']
        string = msgData['string']

        log.info("src and string: %s %s", src, string) 
    
    def setClientid(self):
    # The method is called in the setConfiguration to set a unique clientID  for the client in a group 
    # If there is only one client per host, then the clientId can be the hostname 
    # but if there are more than one clients per host, we will need to add a random int to it... 
        return 

def getAgent(**kwargs):
    agent = Client()
    agent.setConfiguration(None, **kwargs)
    return agent

if __name__ == "__main__":
    agent = Client()
    kwargs = initializeProcessAgent(agent, sys.argv)
    agent.setConfiguration(None, **kwargs)
    agent.run()

import sys
import json
import logging
import random
import socket
from threading import Thread
import threading
import time

from magi.util import helpers


PORT=55343
BUFF=1024
FALSE=0
TXTIMEOUT=1

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

class ClientCommService:
    
    def __init__(self, clientId):
        log.info("In ClientCommService Init")

        self.active = False
        self.clientId = clientId
        self.connected = False
        self.sock = None

        functionName = self.initCommClient.__name__ + str(self.clientId)
        helpers.exitlog(log, functionName, level=logging.INFO)
    
    def initCommClient(self, address, replyHandler):
        functionName = self.initCommClient.__name__
        helpers.entrylog(log, functionName, level=logging.INFO)
        
        self.sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(TXTIMEOUT)
        
        retries = 0        
        while not self.connected:
            log.info("Trying to connect to server, attempt #%d..." % (retries+1))
            try:
                log.info("Trying to connect to server %s..." % (address))
                self.sock.connect((address, PORT))
                self.connected = True
                log.info("Connected to server")
            except socket.error as e:
                retries += 1
                log.info("Socket timed out, exception: %s" % repr(e))
                time.sleep(0.1 + (random.random()*0.3))
                if retries == 10:
                    log.info("Failed to connect after ten retires...  %s" % repr(e))
                    return 

        #data = json.dumps({'src': self.clientId})
        #self.sock.send(data)
        
        self.active = True
        thread = Thread(name="ClientHandler for " + str(self.clientId), target=self.ClientHandler, args=(replyHandler,))
        thread.start()
        
        helpers.exitlog(log, functionName, level=logging.INFO)
        return thread
    
    def ClientHandler(self, replyHandler):
        
        t = threading.currentThread()
        log.info("Running %s"  % t.name)

        data = json.dumps({'src': self.clientId, 'text': 'hello server'})
        self.sock.send(data) 
        
        while self.active:
            #blocks on recv, but may timeout
            try:
                rxdata = self.sock.recv(BUFF)
                log.debug("Data Received: %s" %(repr(rxdata)))
            except socket.timeout:
                continue

            try:
                jdata = json.loads(rxdata.strip())
            except:
                log.info("ClientHandler could not parse JSON string: %s" % repr(rxdata))
                self.stop() 
                continue
            
            log.debug('Client RX jdata: %s'  %(repr(jdata)))
            #replyHandler(jdata)
            self.stop()

        #cleanup
        self.sock.close()
        log.info("Leaving %s" % threading.currentThread().name)
    
    def onesend(self,string):
        data = json.dumps({'src': self.clientId, 'text': string})
        log.debug('Sending data %s' %(data))
        self.sock.send(data)
        


    def sendData(self, data):
        data['src'] = self.clientId
        data = json.dumps(data)
        log.debug('Sending data %s' %(data))
        self.sock.send(data)
                
    def stop(self):
        self.active = False


if __name__ == "__main__":
    client = ClientCommService(sys.argv[1])
    client.initCommClient("127.0.0.1",client.onesend)




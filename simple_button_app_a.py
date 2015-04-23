#!/usr/bin/env python
# simple_button_app_a.py
# Copyright (C) ContinuumBridge Limited, 2015 - All Rights Reserved
# Written by Peter Claydon
#

# Default values:
config = {
    "cid": "none",
}

import sys
import time
from cbcommslib import CbApp
from cbconfig import *
import json
from twisted.internet import reactor

class Client():
    def __init__(self, aid):
        self.aid = aid
        self.count = 0
        self.previousTime = time.time()
        self.messages = []

    def send(self, data):
        message = {
                   "source": self.aid,
                   "destination": config["cid"],
                   "body": data
                  }
        message["body"]["n"] = self.count
        self.count += 1
        self.messages.append(message)
        self.sendMessage(message, "conc")

    def receive(self, message):
        #self.cbLog("debug", "Message from client: " + str(message))
        if "body" in message:
            if "n" in message["body"]:
                #self.cbLog("debug", "Received ack from client: " + str(message["body"]["n"]))
                for m in self.messages:
                    if m["body"]["n"] == m:
                        self.messages.remove(m)
                        self.cbLog("debug", "Removed message " + str(m) + " from queue")
        else:
            self.cbLog("warning", "Received message from client with no body")

class App(CbApp):
    def __init__(self, argv):
        self.appClass = "monitor"
        self.state = "stopped"
        self.devices = []
        self.status = "ok"
        self.idToName = {} 
        self.sensorsID = []
        #CbApp.__init__ MUST be called
        CbApp.__init__(self, argv)

    def setState(self, action):
        if action == "clear_error":
            self.state = "running"
        else:
            self.state = action
        msg = {"id": self.id,
               "status": "state",
               "state": self.state}
        self.sendManagerMessage(msg)

    def onConcMessage(self, message):
        try:
            self.client.receive(message)
        except Exception as ex:
            self.cbLog("debug", "message received from client before app configured")
            self.cbLog("warning", "Exception: " + str(type(ex)) + str(ex.args))

    def onAdaptorData(self, message):
        self.cbLog("debug", "onadaptorData, message: " + str(json.dumps(message, indent=4)))
        now = time.time()
        if now - self.previousTime > 3:
            self.cbLog("debug", "onAdaptorData, button received")
            self.previousTime = now
            msg = {"m": "button",
                   "s": self.idToName[message["id"]],
                   "t": time.time()
                  }
            self.client.send(msg)

    def onAdaptorService(self, message):
        buttons = False
        button = False
        number_buttons = False
        for p in message["service"]:
            if p["characteristic"] == "buttons":
                buttons = True
            if p["characteristic"] == "number_buttons":
                number_buttons = True
            if p["characteristic"] == "button":
                button = True
        if buttons:
            self.sensorsID.append(message["id"])
            req = {"id": self.id,
                   "request": "service",
                   "service": [
                                 {"characteristic": "buttons",
                                  "interval": 0
                                 }
                              ]
                  }
            self.sendMessage(req, message["id"])
        if number_buttons:
            self.sensorsID.append(message["id"])
            req = {"id": self.id,
                   "request": "service",
                   "service": [
                                 {"characteristic": "number_buttons",
                                  "interval": 0
                                 }
                              ]
                  }
            self.sendMessage(req, message["id"])
        if button:
            self.sensorsID.append(message["id"])
            req = {"id": self.id,
                   "request": "service",
                   "service": [
                                 {"characteristic": "button",
                                  "interval": 0
                                 }
                              ]
                  }
            self.sendMessage(req, message["id"])
        self.setState("running")

    def onConfigureMessage(self, managerConfig):
        global config
        configFile = CB_CONFIG_DIR + "simple_button_app.config"
        try:
            with open(configFile, 'r') as f:
                newConfig = json.load(f)
                self.cbLog("debug", "Read simple_button_app.config")
                config.update(newConfig)
        except Exception as ex:
            self.cbLog("warning", "simple_button_app.config does not exist or file is corrupt")
            self.cbLog("warning", "Exception: " + str(type(ex)) + str(ex.args))
        for c in config:
            if c.lower in ("true", "t", "1"):
                config[c] = True
            elif c.lower in ("false", "f", "0"):
                config[c] = False
        self.cbLog("debug", "Config: " + str(json.dumps(config, indent=4)))
        for adaptor in managerConfig["adaptors"]:
            adtID = adaptor["id"]
            if adtID not in self.devices:
                # Because managerConfigure may be re-called if devices are added
                name = adaptor["name"]
                friendly_name = adaptor["friendly_name"]
                self.cbLog("debug", "managerConfigure app. Adaptor id: " +  adtID + " name: " + name + " friendly_name: " + friendly_name)
                self.idToName[adtID] = friendly_name
        self.client = Client(self.id)
        self.client.sendMessage = self.sendMessage
        self.client.cbLog = self.cbLog
        self.setState("starting")

if __name__ == '__main__':
    App(sys.argv)

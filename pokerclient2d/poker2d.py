#
# Copyright (C) 2004, 2005 Mekensleep
#
# Mekensleep
# 24 rue vieille du temple
# 75004 Paris
#       licensing@mekensleep.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# Authors:
#  Loic Dachary <loic@gnu.org>
#
import sys
sys.path.insert(0, "..")

import os
from string import split, lower
from os import makedirs
from os.path import expanduser, exists
import signal
from traceback import print_exc
import libxml2
from shutil import copy

from time import sleep
from random import choice, uniform, randint

from pokernetwork.config import Config

default_settingsfile = "/usr/share/poker-network/poker2d/poker2d.xml"
user_dir = expanduser("~/.poker2d")
settingsfile = len(sys.argv) > 1 and sys.argv[1] or user_dir + "/poker2d.xml"
configfile = len(sys.argv) > 2 and sys.argv[2] or "client.xml"

if os.name == "posix":
    conf_file = user_dir + "/poker2d.xml"
    if not exists(conf_file) and exists(default_settingsfile):
        if not exists(user_dir):
            makedirs(user_dir)
        copy(default_settingsfile, user_dir)

class Main:
    "Poker gameplay"

    def __init__(self, configfile, settingsfile):
        self.settings = Config([''])
        self.settings.load(settingsfile)
        self.shutting_down = False
        if self.settings.header:
            rcdir = self.configureDirectory()
            self.dirs = split(self.settings.headerGet("/settings/path"))
            self.config = Config(self.dirs)
            self.config.load(configfile)
            self.verbose = self.settings.headerGetInt("/settings/@verbose")
            self.poker_factory = None
#            sleep(12) # we would like this feature on windows (in dev)

    def configOk(self):
        return self.settings.header and self.config.header

    def shutdown(self, signal, stack_frame):
        self.shutting_down = True
        self.poker_factory.display.finish()
        if self.verbose:
            print "received signal %s, exiting" % signal
            
    def configureDirectory(self):
        settings = self.settings
        if not settings.headerGet("/settings/user/@path"):
            print """
No <user path="user/settings/path" /> found in file %s.
Using current directory instead.
""" % settings.url
            return
        
        rcdir = expanduser(settings.headerGet("/settings/user/@path"))
        if not exists(rcdir):
            os.mkdir(rcdir)

    def run(self):
        settings = self.settings
        config = self.config

        signal.signal(signal.SIGINT, self.shutdown)
        if os.name == "posix":
            signal.signal(signal.SIGQUIT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

        poker_factory = PokerClientFactory2D(settings = settings,
                                             config = config)
        self.poker_factory = poker_factory

        try:
            poker_factory.display.run()
        except:
            print_exc()

        poker_factory.children.killall()
        poker_factory.display.finish()
        poker_factory.display = None

client = Main(configfile, settingsfile)

from twisted.internet import gtk2reactor
gtk2reactor.install()
from twisted.internet import reactor
from twisted.internet import error

from pokernetwork.pokerclient import PokerClientFactory
from pokernetwork.pokerpackets import *

from pokerui import pokerinterface
from pokerui.pokerrenderer import PokerRenderer

from pokerclient2d.pokerdisplay2d import PokerDisplay2D
from pokerclient2d.pokerinterface2d import PokerInterface2D

class PokerClientFactory2D(PokerClientFactory):
    def __init__(self, *args, **kwargs):
        PokerClientFactory.__init__(self, *args, **kwargs)

        self.renderer = PokerRenderer(self)
        self.interface = None
        self.initDisplay()

        self.interface = PokerInterface2D(self.settings)
        self.showServers()
        self.renderer.interfaceReady(self.interface)

    def quit(self, dummy = None):
        interface = self.interface
        if interface:
            if not interface.callbacks.has_key(pokerinterface.INTERFACE_YESNO):
                interface.yesnoBox("Do you really want to quit ?")
                interface.registerHandler(pokerinterface.INTERFACE_YESNO, self.confirmQuit)
        else:
            self.confirmQuit(True)

    def confirmQuit(self, response):
        if response:
            #
            # !!! The order MATTERS here !!! underware must be notified last
            # otherwise leak detection won't be happy. Inverting the two
            # is not fatal and the data will be freed eventually. However,
            # debugging is made much harder because leak detection can't
            # check as much as it could.
            #
            self.renderer.confirmQuit()
            packet = PacketQuit()
            self.display.render(packet)

    def initDisplay(self):
        self.display = PokerDisplay2D(settings = self.settings,
                                      config = self.config,
                                      factory = self)

        self.display.init()
            
    def showServers(self):
        servers = split(self.settings.headerGet("/settings/servers"))
        if len(servers) > 1:
            interface = self.interface
            interface.chooser("Choose a poker server", servers)
            interface.registerHandler(pokerinterface.INTERFACE_CHOOSER, self.selectServer)
        else:
            self.selectServer(servers[0])
            
    def selectServer(self, server):
        (self.host, self.port) = split(server, ":")
        self.port = int(self.port)
        settings = self.settings
        reactor.connectTCP(self.host,
                           self.port,
                           self,
                           settings.headerGetInt("/settings/@tcptimeout"))
        

    def buildProtocol(self, addr):
        protocol = PokerClientFactory.buildProtocol(self, addr)
        self.renderer.setProtocol(protocol)
        self.display.setProtocol(protocol)
        return protocol

    def clientConnectionFailed(self, connector, reason):
        print "connectionFailed: %s" % reason
        self.interface.messageBox("Unable to reach the poker\nserver at %s:%d" % ( self.host, self.port ))
        self.interface.registerHandler(pokerinterface.INTERFACE_MESSAGE_BOX, self.showServers)
        
    def clientConnectionLost(self, connector, reason):
        self.renderer.setProtocol(None)
        reconnect = True
        if hasattr(self, "reconnect"):
            reconnect = self.reconnect
            del self.reconnect

        if reconnect:
            message = "The poker server connection was closed"
            if not reason.check(error.ConnectionDone):
                message += " " + str(reason)
            print message
            if self.interface:
                self.interface.messageBox("Lost connection to poker\nserver at %s:%d" % ( self.host, self.port ))
                self.interface.registerHandler(pokerinterface.INTERFACE_MESSAGE_BOX, self.showServers)
    
if client.configOk():
    try:
        client.run()
#        import profile
#        profile.run('client.run()', 'bar')
#        import pstats
#        pstats.Stats('bar').sort_stats().print_stats()
    except:
        if client.verbose:
            print_exc()
        else:
            print sys.exc_value

#
# Emacs debug:
# M-x pdb
# pdb poker2d.py poker2d.xml
#

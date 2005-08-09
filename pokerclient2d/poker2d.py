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
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301, USA.
#
# Authors:
#  Loic Dachary <loic@gnu.org>
#
import sys
sys.path.insert(0, "..")

#
# Workaround for the twisted-2.0 bug 
# http://twistedmatrix.com/bugs/issue1083
#
#import gobject
#if hasattr(gobject, "threads_init"):
#    del gobject.threads_init

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
from pokernetwork import version

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

from twisted.internet import gtk2reactor
gtk2reactor.install()
from twisted.internet import reactor
#
# Workaround for the twisted-2.0 bug 
# http://twistedmatrix.com/bugs/issue1083
#
try:
    from twisted.internet.base import BlockingResolver
    reactor.installResolver(BlockingResolver())
except:
    pass
from twisted.internet import error

from pokernetwork.pokerclient import PokerClientFactory, PokerSkin
from pokernetwork.pokerpackets import *

from pokerui import pokerinterface
from pokerui.pokerrenderer import PokerRenderer

from pokerclient2d.pokerdisplay2d import PokerDisplay2D
from pokerclient2d.pokerinterface2d import PokerInterface2D

import gtk

class PokerSkin2D(PokerSkin):
    def __init__(self, *args, **kwargs):
        PokerSkin.__init__(self, *args, **kwargs)
        color = gtk.ColorSelectionDialog("Outfit selection")
        color.ok_button.connect("clicked", self.colorSelected)
        color.cancel_button.connect("clicked", self.colorSelectionCanceled)
        self.color_dialog = color
        self.select_callback = None
        ( self.url, self.outfit ) = self.interpret(self.url, self.outfit)

    def interpret(self, url, outfit):
        if outfit == "random" or "<?xml" in outfit:
            outfit = "#%02x%02x%02x" % ( randint(100,255), randint(100,255), randint(100,255) )
        return (url, outfit)

    def hideOutfitEditor(self):
        self.color_dialog.hide()

    def showOutfitEditor(self, select_callback):
        self.select_callback = select_callback
        self.color_dialog.show()

    def colorSelected(self, *args):
        color = self.color_dialog.colorsel.get_current_color()
        outfit = "#%02x%02x%02x" % ( (color.red >> 8), (color.green >> 8), (color.blue >> 8) )
        self.select_callback("random", outfit)

    def colorSelectionCanceled(self, *args):
        self.select_callback("random", None)
        
class PokerClientFactory2D(PokerClientFactory):
    def __init__(self, *args, **kwargs):
        PokerClientFactory.__init__(self, *args, **kwargs)

        self.skin = PokerSkin2D(settings = self.settings)
        self.renderer = PokerRenderer(self)
        self.interface = None
        self.initDisplay()

        self.interface = PokerInterface2D(self.settings)
        self.skin.interfaceReady(self.interface, self.display)
        self.renderer.interfaceReady(self.interface)
        if self.settings.headerGet("/settings/@upgrades") == "yes":
            self.checkClientVersion((version.major, version.medium, version.minor))
        else:
            self.clientVersionOk()

    def clientVersionOk(self):
        self.showServers()

    def needUpgrade(self, version):
        interface = self.interface
        interface.yesnoBox("A new client version is available, do you want to upgrade now ?")
        interface.registerHandler(pokerinterface.INTERFACE_YESNO, lambda result: self.upgradeConfirmed(result, version))

    def upgradeConfirmed(self, confirmed, version):
        if confirmed:
            self.upgrade(version, ("poker2d.xml", ))
        else:
            self.quit()

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
        if ";" in self.port:
            (self.port, want_ssl) = split(self.port, ";")
        else:
            want_ssl = None
        self.port = int(self.port)
        settings = self.settings
        timeout = settings.headerGetInt("/settings/@tcptimeout")
        if want_ssl:
            from twisted.internet import ssl
            reactor.connectSSL(self.host,
                               self.port,
                               self,
                               ssl.ClientContextFactory(),
                               timeout)
        else:
            reactor.connectTCP(self.host,
                               self.port,
                               self,
                               timeout)
        

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
                self.interface.registerHandler(pokerinterface.INTERFACE_MESSAGE_BOX, self.quit)
    
def run(argv, default_settingsfile):
    user_dir = expanduser("~/.poker2d")
    settingsfile = len(argv) > 1 and argv[1] or user_dir + "/poker2d.xml"
    configfile = len(argv) > 2 and argv[2] or "client.xml"

    if os.name == "posix":
        conf_file = user_dir + "/poker2d.xml"
        if not exists(conf_file) and exists(default_settingsfile):
            if not exists(user_dir):
                makedirs(user_dir)
            copy(default_settingsfile, user_dir)


    client = Main(configfile, settingsfile)

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

if __name__ == "__main__":
    run(sys.argv, "")
#
# Emacs debug:
# M-x pdb
# pdb poker2d.py poker2d-test.xml
#

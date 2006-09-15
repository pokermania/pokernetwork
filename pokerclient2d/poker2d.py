#
# Copyright (C) 2004, 2005, 2006 Mekensleep
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
import platform
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

from twisted.internet import ssl
from twisted.python import log

from pokernetwork.pokernetworkconfig import Config
from pokernetwork.version import version
from pokernetwork.proxy import Connector

from twisted.internet.gtk2reactor import Gtk2Reactor

class Poker2DReactor(Gtk2Reactor):
    
    def simulate(self):
        if log.error_occurred:
            reactor.stop()
        Gtk2Reactor.simulate(self)
        
from twisted.internet.main import installReactor
reactor = Poker2DReactor()
installReactor(reactor)

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

from pokerui.pokerdisplay import PokerDisplay
from pokerclient2d.pokerdisplay2d import PokerDisplay2D
from pokerclient2d.pokerinterface2d import PokerInterface2D

import gtk

class Main:
    "Poker gameplay"

    def __init__(self, configfile, settingsfile):
        self.settings = Config([''])
        self.settings.load(settingsfile)
        self.shutting_down = False
        if self.settings.header:
            rcdir = self.configureDirectory()
            self.dirs = split(self.settings.headerGet("/settings/path"))
            self.config = Config([''] + self.dirs)
            self.config.load(configfile)
            self.verbose = self.settings.headerGetInt("/settings/@verbose")
            self.poker_factory = None

    def configOk(self):
        return self.settings.header and self.config.header

    def shutdown(self, signal, stack_frame):
        self.shutting_down = True
        self.poker_factory.display.finish()
        reactor.stop()
        if self.verbose:
            print "received signal %s, exiting" % signal
            
    def configureDirectory(self):
        settings = self.settings
        if not settings.headerGet("/settings/user/@path"):
            print """
No <user path="user/settings/path" /> found in file %s.
Using current directory instead.
""" % settings.path
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

        poker_factory = None
        
        try:
            poker_factory = PokerClientFactory2D(settings = settings,
                                                 config = config)
            self.poker_factory = poker_factory

            if poker_factory.display:
                reactor.run()
            else:
                raise Exception, "PokerClientFactory2D instance has no display" 
        except:
            print_exc()

        if poker_factory:
            if poker_factory.children:
                poker_factory.children.killall()
            if poker_factory.display:
                poker_factory.display.finish()
                poker_factory.display = None

class PokerSkin2D(PokerSkin):
    def __init__(self, *args, **kwargs):
        PokerSkin.__init__(self, *args, **kwargs)
        color = gtk.ColorSelectionDialog("Outfit selection")
        color.ok_button.connect("clicked", self.colorSelected)
        color.cancel_button.connect("clicked", self.colorSelectionCanceled)
        self.color_dialog = color
        self.select_callback = None

    def interpret(self, url, outfit):
        if outfit == "random" or "<?xml" in outfit:
            outfit = "#%02x%02x%02x" % ( randint(100,255), randint(100,255), randint(100,255) )
        return (url, outfit)

    def hideOutfitEditor(self):
        self.color_dialog.hide()

    def showOutfitEditor(self, select_callback):
        self.select_callback = select_callback
        color = gtk.gdk.color_parse(self.outfit)
        self.color_dialog.colorsel.set_current_color(color)
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

        self.initDisplay()
        if self.settings.headerGet("/settings/@batch") != "yes":
            self.skin = PokerSkin2D(settings = self.settings)
            self.renderer = PokerRenderer(self)
            self.initDisplay()

            self.interface = PokerInterface2D(self.settings)
            self.skin.interfaceReady(self.interface, self.display)
            self.renderer.interfaceReady(self.interface)
 
        if self.settings.headerGet("/settings/@upgrades") == "yes":
            self.checkClientVersion((version.major(), version.medium(), version.minor()))
        else:
            self.clientVersionOk()

    def clientVersionOk(self):
        if self.settings.headerGet("/settings/@batch") == "yes":
            self.quit()
        else:
            self.showServers()

    def failedUpgrade(self, logs, reason):
        message = "Unable to upgrade software\n" + logs
        if self.settings.headerGet("/settings/@batch") == "yes":
            print message
        else:
            interface = self.interface
            interface.messageBox(message)
            interface.registerHandler(pokerinterface.INTERFACE_MESSAGE_BOX, lambda: self.quit())
        
    def needUpgrade(self, version):
        if self.settings.headerGet("/settings/@batch") == "yes":
            self.upgradeConfirmed(confirmed = True, version = version)
            print "Upgrading to client version " + str(version)
        else:
            interface = self.interface
            interface.yesnoBox("Client version " + str(version) + " is available, do you want to upgrade now ?")
            interface.registerHandler(pokerinterface.INTERFACE_YESNO, lambda result: self.upgradeConfirmed(result, version))

    def upgradeConfirmed(self, confirmed, version):
        if confirmed:
            self.upgrade(version, ("poker2d.xml", ))
        else:
            self.quit()

    def initDisplay(self):
        if self.settings.headerGet("/settings/@batch") == "yes":
            self.display = PokerDisplay(settings = self.settings,
                                        config = self.config,
                                        factory = self)
        else:
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

        ssl_context = want_ssl and ssl.ClientContextFactory()
        
        settings = self.settings
        proxy = settings.headerGet("/settings/servers/@proxy")
        if proxy:
            if self.verbose > 1:
                print "connection thru proxy " + proxy
            ( host, port ) = proxy.split(':')
            port = int(port)
        else:
            ( host, port ) = ( self.host, self.port )

        timeout = settings.headerGetInt("/settings/@tcptimeout")

        c = Connector(host, port, self, ssl_context, timeout, None, reactor)
        if proxy:
            c.setProxyHost("%s:%d" % (self.host, self.port))
        c.connect()

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
    
def run(datadir, settings_file, config_file):
    user_dir = expanduser("~/.poker2d")
    if not settings_file: settings_file = user_dir + "/poker2d.xml"
    if not config_file: config_file = "client.xml"

    Config.upgrades_repository = datadir + "/upgrades"
    
    if platform.system() == "Windows":
        raise UserWarning, "can't infer the location of the settings file on Windows (not yet implemented)"

    default_settings_file = datadir + "/poker2d.xml"
    if not exists(settings_file) and exists(default_settings_file):
        if not exists(user_dir):
            makedirs(user_dir)
        copy(default_settings_file, settings_file)

    client = Main(config_file, settings_file)

    if client.configOk():
        client.run()

if __name__ == "__main__":
    config_file = None
    settings_file = None
    if len(sys.argv) > 1:
        settings_file = sys.argv[1]
    if len(sys.argv) > 2:
        config_file = sys.argv[2]
    run(".", settings_file, config_file)
#
# Emacs debug:
# M-x pdb
# pdb poker2d.py poker2d-test.xml
#

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
#  Henry Precheur <henry@precheur.org>
#
#

# tiny example to test poker3d-interface

import getopt, sys

from twisted.internet.protocol import Protocol, Factory
from twisted.internet import reactor
from time import sleep

verbose = 0

step = 1
class InterfaceProtocol(Protocol):
    def connectionMade(self):
        if self.factory.module:
            eval('self.' + self.factory.module + '()')
        else:
            self.blind()
            self.buy_in()
            self.menu()
            self.cashier()
            self.chat()
            self.login()
            self.message_box()
            self.yesno()
            self.sit_actions()
            self.chooser()
            self.menu()
            self.outfits()
            self.tournaments()
            #self.lobby()
            self.muck()
            self.check_warning()
            reactor.callLater(60, lambda: self.command('quit'))

    def command(self, *args):
        global verbose
        if verbose: print str(args)
        self.transport.write("\000".join(args) + "\000")

    def tournaments(self):
        delay = 5
        reactor.callLater(delay, lambda: self.command("tournaments", "show", "cashier_label", "sit_n_go", "n"))
        delay += 1
        reactor.callLater(delay, lambda: self.command("tournaments", "sit_n_go",
                                                            "1",
                                                            "2",
                                                            "1", "Sitngo 1", "registering", "5/10",
                                                            "2", "Sitngo 2", "registering", "7/10"))
        return
        delay += 1
        reactor.callLater(delay, lambda: self.command("tournaments", "sit_n_go",
                                                            "2",
                                                            "1", "Sitngo 3", "registering", "5/10",
                                                            "2", "Sitngo 4", "registering", "7/10"))
        delay += 1 
        reactor.callLater(delay, lambda: self.command("tournaments", "regular",
                                                            "2",
                                                            "10", "2004/05/07", "Regular 1", "registering", "250",
                                                            "20", "2003/04/06", "Regular 2", "registering", "312"))
        
        delay += 1 
        reactor.callLater(delay, lambda: self.command("tournaments", "players",
                                                            "20",
                                                            "player 1",
                                                            "player 2",
                                                            "player 3",
                                                            "player 4",
                                                            "player 5",
                                                            "player 6",
                                                            "player 7",
                                                            "player 8",
                                                            "player 9",
                                                            "player 10",
                                                            "player 11",
                                                            "player 12",
                                                            "player 13",
                                                            "player 14",
                                                            "player 15",
                                                            "player 16",
                                                            "player 17",
                                                            "player 18",
                                                            "player 19",
                                                            "player 20",
                                                            ))
        
    def chooser(self):
        delay = 0
        reactor.callLater(delay, lambda: self.command("chooser", "Chooser a server", "3", "server1", "server2", "server3"))
        
    def cashier(self):
        messages = ( "Foo Bar",
                     "foo@bar.com",
                  "My address",
                  "15000",
                  "10",
                  "15010",
                  "15000$",
                  "10$",
                  "15010$" )
        packet = [ "cashier", "show", "%d" % len(messages) ]
        packet.extend(messages)
	packet.append("exit_label")
        reactor.callLater(5, lambda: self.command(*packet))

    def menu(self):
        delay = 0
        reactor.callLater(delay, lambda: self.command("menu", "show"))
        delay += 1
        reactor.callLater(delay, lambda: self.command("menu", "set", "resolution", "800x600"))
        delay += 1
        reactor.callLater(delay, lambda: self.command("menu", "set", "shadow", "yes"))
        
    def message_box(self):
        delay = 0
        reactor.callLater(delay, lambda: self.command("message_box", "my message!"))

    def blind(self):
        delay = 0
        reactor.callLater(delay, lambda: self.command("blind", "show"))
        delay += 1
        reactor.callLater(delay, lambda: self.command("blind", "blind message", "Pay the blind ?", "yes"))
        delay += 10
        reactor.callLater(delay, lambda: self.command("blind", "hide"))

    def yesno(self):
        delay = 0
        reactor.callLater(delay, lambda: self.command("yesno", "Do you want or don't you want ?"))

    def muck(self):
        delay = 0
        reactor.callLater(delay, lambda: self.command("muck"))

    def check_warning(self):
        delay = 0
        reactor.callLater(delay, lambda: self.command("check_warning"))

    def login(self):
        delay = 0
        reactor.callLater(delay, lambda: self.command("login", "henry", "blabla", "1"))

    def chat(self):
        delay = 0
        reactor.callLater(delay, lambda: self.command("chat", "show"))
        delay += 1
        reactor.callLater(delay, lambda: self.command("chat", "line", "line 1\n"))
        delay += 1
        reactor.callLater(delay, lambda: self.command("chat", "line", "line 2\n"))
        delay += 1
        reactor.callLater(delay, lambda: self.command("chat", "line", "line 2\nline 2\nline 2\nline 2\nline 2\nline 2\nline 2\nline 2\n"))
        reactor.callLater(delay, lambda: self.command("chat", "line", "line 2\nline 2\nline 2\nline 2\nline 2\nline 2\nline 2\nline 2\n"))
        delay += 1
        reactor.callLater(delay, lambda: self.command("chat", "line", "line 3\n"))
        delay += 20
        reactor.callLater(delay, lambda: self.command("chat", "hide"))
        
    def buy_in(self):
        delay = 0
        reactor.callLater(delay, lambda: self.command("buy_in", "show"))
        delay += step
        reactor.callLater(delay, lambda: self.command("buy_in", "params", "20", "300.0", "Which amount?", "All your bankroll"))
        reactor.callLater(delay, lambda: self.command("buy_in", "hide"))
        delay += step
        reactor.callLater(delay, lambda: self.command("buy_in", "show"))

    def lobby(self):
        info = ( '1',	#str(table.id),
        'yes',			#my,
        'One',			#table.name,
        'limit 2/4',	#file2name(table.betting_structure),
        '2',			#str(table.seats),
        '3',			#str(table.average_pot),
        '4',			#str(table.hands_per_hour),
        '5',			#str(table.percent_flop),
        '6',			#str(table.players),
        '7',			#str(table.observers),
        '8',			#str(table.waiting),
        '9',			#str(table.timeout)
        )
        packet = ['lobby', 'holdem', '0', '1']
        packet.extend(info)
        self.command(*packet)
        self.command('lobby', 'info', "Players: %d" % 10, "Tables: %d" % 11)
        self.command("lobby", "show", "Cashier", "holdem", "n")

    def outfits(self):
        reactor.callLater(0, lambda: self.command("outfit", "show"))
        packet = ( "outfit", "set", "female", "2", 
                   "Slot", "1", "5", "2",
                   "1",
                   "Opacity", "opacity", "0", "5", "2",
                   "file", "1", "opacity_%d.png" )
        reactor.callLater(1, lambda: self.command(*packet))
        packet = ( "outfit", "set", "male", "8", 
                   "Slot", "1", "5", "2",
                   "3",
                   "Color", "color", "0", "3", "1",
                   "basecolor", "3", "#ff00ff", "#ff1111", "#11ff11",
                   "Detail Color", "color", "0", "3", "1",
                   "detailcolor", "3", "#ff00ff", "#ff1111", "#11ff11", 
                   "Opacity", "opacity", "0", "2", "0",
                   "file", "1", "opacity_%d.png" )
        reactor.callLater(2, lambda: self.command(*packet))
        
    def sit_actions(self):
        delay = 0
        reactor.callLater(delay, lambda: self.command("sit_actions", "show"))
        delay += step
        reactor.callLater(delay, lambda: self.command("sit_actions", "auto", "yes"))
        delay += step
        reactor.callLater(delay, lambda: self.command("sit_actions", "auto", "no"))
        delay += step
        reactor.callLater(delay, lambda: self.command("sit_actions", "sit_out", "yes", "Sit back"))
        delay += step
        reactor.callLater(delay, lambda: self.command("sit_actions", "sit_out", "no", "Sitout"))
        delay += step
        reactor.callLater(delay, lambda: self.command("sit_actions", "sit_out", "yes", "Come back"))
        delay += step
        reactor.callLater(delay, lambda: self.command("sit_actions", "hide"))
        delay += step
        reactor.callLater(delay, lambda: self.command("sit_actions", "show"))
    
    def dataReceived(self, data):
        print "%s" % data

class InterfaceFactory(Factory):
    def __init__(self, module):
        self.module = module

def main():
    global verbose
    
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hvmp", ["help", "verbose=", "module=", "port=" ])
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    module = None
    port = 19379
    dry_run = False
    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit(0)
        if o in ("-m", "--module"):
            module = a
        if o in ("-p", "--port"):
            port = int(a)
        if o in ("-v", "--verbose"):
            verbose = int(a)

    factory = InterfaceFactory(module)
    factory.protocol = InterfaceProtocol
    reactor.listenTCP(port, factory)
    if verbose: print "started"
    reactor.run()

if __name__ == '__main__':
    main()

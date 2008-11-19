#
# Copyright (C) 2004, 2005, 2006 Mekensleep <licensing@mekensleep.com>
#                                24 rue vieille du temple, 75004 Paris
#       
# This software's license gives you freedom; you can copy, convey,
# propogate, redistribute and/or modify this program under the terms of
# the GNU Affero General Public License (AGPL) as published by the Free
# Software Foundation, either version 3 of the License, or (at your
# option) any later version of the AGPL.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero
# General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program in a file in the toplevel directory called
# "AGPLv3".  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#  Loic Dachary <loic@gnu.org>
#
import sys
sys.path.insert(0, "../pokerclient2d")
from twisted.internet.protocol import Protocol, Factory
from twisted.internet import gtk2reactor
gtk2reactor.install()
from twisted.internet import reactor
from time import sleep
import cpokerinterface
import gtk

def makeTables(tables):
    packet = []
    variants = {}
    for table in tables:
        if not variants.has_key(table['variant']):
            variants[table['variant']] = []
        variants[table['variant']].append(table)
    packet.append("lobby")
    packet.append("table_list")
    packet.append("Tables: 3")
    packet.append("Players: 10") 
    packet.append("Choose a poker table to join")
    packet.append("%d" % len(variants)) # number of tabs
    variant_names = variants.keys()
    variant_names.sort()
    for variant in variant_names:
        packet.append("%d" % 11) # number of fields
        packet.extend(("0", "1", "1", "0", "0", "0", "0", "0", "0", "0", "0")) # field types
        packet.extend(("id", "name", "structure", "seats", "avg. pot", "hands/h", "%flop", "playing", "observing", "waiting", "timeout")) # headers
        packet.append("%d" % len(variants[variant]))
        for table in variants[variant]:
            packet.append("%d" % table['id'])
            packet.append("%s" % table['name'])
            packet.append("%s" % table['betting_structure'])
            packet.append("%d" % table['seats'])
            packet.append("%d" % table['average_pot'])
            packet.append("%d" % table['hands_per_hour'])
            packet.append("%d" % table['percent_flop'])
            packet.append("%d" % table['players'])
            packet.append("%d" % table['observers'])
            packet.append("%d" % table['waiting'])
            packet.append("%d" % table['timeout'])
        packet.append("%s" % variant)
    return packet

step = 1
class InterfaceTest:
    def __init__(self):
        cpokerinterface.init(callback = self.event,
                            glade = "../pokerclient2d/data/interface/interface2d.glade",
#                            gtkrc = "../pokerclient2d/data/Aero/gtkrc",
                            verbose = 3)
        window = gtk.Window()
        window.set_default_size(1024,768)
        window.set_title("Poker Interface")
        window.set_name("lobby_window_root")
        self.screen = gtk.Layout()
        self.screen.set_size(1024,768)
        self.screen.set_name("screen")
        window.add(self.screen)
        window.show_all()

    def event(self, *args):
        print "event: " + str(args)
    
    def command(self, *args):
        print args
        cpokerinterface.command(self.screen, *args)

    def connectionMade(self):
        #self.blind()
        #self.buy_in()
        #self.cashier()
        #self.chat()
        #self.table_list()
        #self.login()
        #self.message_box()
        #self.yesno()
        #self.sit_actions()
        #self.chooser()
        #self.menu()
        #self.outfits()
        #self.tournaments()
        reactor.callLater(60, lambda: reactor.stop())

    def tournaments(self):
        delay = 0
        reactor.callLater(delay, lambda: self.command("tournaments", "show"))
        delay += 1
        reactor.callLater(delay, lambda: self.command("tournaments", "sitngo",
                                                            "2",
                                                            "1", "Sitngo 1", "registering", "5/10",
                                                            "2", "Sitngo 2", "registering", "7/10"))
        delay += 1
        reactor.callLater(delay, lambda: self.command("tournaments", "sitngo",
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
                                                            "1",
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
        reactor.callLater(0, lambda: self.command(*packet))

    def menu(self):
        delay = 0
        reactor.callLater(delay, lambda: self.command("menu", "show"))
        delay += 1
        reactor.callLater(delay, lambda: self.command("menu", "set", "resolution", "800x600"))
        delay += 1
        reactor.callLater(delay, lambda: self.command("menu", "set", "shadow", "yes"))
        
    def message_box(self):
        delay = 0
        reactor.callLater(delay, lambda: self.command("message_box", "my message! This is a long message\nto show how it wraps"))

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

    def table_list(self):
        packet = makeTables([
            {'name': 'table 1',
             'variant': 'holdem',
             'betting_structure': 'limit 2/4',
             'id': 1,
             'seats': 5,
             'average_pot': 150,
             'hands_per_hour': 30,
             'percent_flop': 60,
             'players': 5,
             'observers': 5,
             'waiting': 5,
             'timeout': 5,
             },
            {'name': 'table 2',
             'variant': 'holdem',
             'betting_structure': 'limit 2/4',
             'id': 2,
             'seats': 5,
             'average_pot': 150,
             'hands_per_hour': 30,
             'percent_flop': 60,
             'players': 5,
             'observers': 5,
             'waiting': 5,
             'timeout': 5,
             }])
        print "packet %s" % packet
        reactor.callLater(0, lambda: self.command(*packet))

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

def main():
    i = InterfaceTest()
    i.connectionMade()
    reactor.run()

if __name__ == '__main__':
    main()

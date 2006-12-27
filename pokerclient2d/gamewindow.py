# -*- mode: python -*-
#
# Copyright (C) 2006 Mekensleep
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
#  Johan Euphrosine <johan@mekensleep.com>
#

import gtk
import gtk.glade
import unittest

class GameWindowGlade:
    def __init__(self):
        self.widgets = {}
        self.glade = gtk.glade.XML('data/skin/mockup.glade')
        window = self.glade.get_widget('game_window')
        fixed = self.glade.get_widget('game_fixed')
        window.remove(fixed)
        event = gtk.EventBox()
        event.set_name("game_window")
        self.widgets[event.get_name()] = event
        event.add(fixed)
        for seat_index in range(0, 10):
            seat = self.glade.get_widget('sit_seat%d' % seat_index)
            (x, y) = (fixed.child_get_property(seat, 'x'), fixed.child_get_property(seat, 'y'))
            for card_index in range(1, 8):
                image = gtk.Image()
                image.set_name("card%d_seat%d" % (card_index, seat_index))
                fixed.put(image, x+(card_index-1)*10, y+20)
                self.widgets[image.get_name()] = image
        for board_index in range(1, 6):
            board = self.glade.get_widget('board%d' % board_index)
            (x, y) = (fixed.child_get_property(board, 'x'), fixed.child_get_property(board, 'y'))           
            image = gtk.Image()
            image.set_name('board%d' % (board_index))
            fixed.remove(board)
            fixed.put(image, x, y)
            self.widgets[image.get_name()] = image
        winner_up = self.glade.get_widget('winner0')
        (x, y) = (fixed.child_get_property(winner_up, 'x'), fixed.child_get_property(winner_up, 'y'))
        fixed.remove(winner_up)
        for winner_index in range(4):
            winner = gtk.Label()
            winner.set_name('winner%d' % winner_index)
            self.widgets[winner.get_name()] = winner
            fixed.put(winner, x, y - winner_index*10)
        winner_down = self.glade.get_widget('winner1')
        (x, y) = (fixed.child_get_property(winner_down, 'x'), fixed.child_get_property(winner_down, 'y'))
        fixed.remove(winner_down)
        for winner_index in range(4, 9):
            winner = gtk.Label()
            winner.set_name('winner%d' % winner_index)
            self.widgets[winner.get_name()] = winner
            fixed.put(winner, x, y + (winner_index-5)*10)
        table_status = gtk.TextView()
        table_status.set_name("table_status")
        fixed.put(table_status, 0, 0)
        self.widgets[table_status.get_name()] = table_status
	accelerators = ("raise_increase",
                        "raise_decrease",
                        "raise_increase_bb",        
                        "raise_decrease_bb",
                        "raise_pot",
                        "raise_half_pot")
        for accelerator in accelerators:
            button = gtk.Button()
            button.set_name(accelerator)
            fixed.put(button, 0, 0)
            self.widgets[button.get_name()] = button
        raise_range = self.glade.get_widget("raise_range")
        (x, y) = (fixed.child_get_property(raise_range, 'x'), fixed.child_get_property(raise_range, 'y'))
        fixed.remove(raise_range)
        raise_range = gtk.HScale()
        fixed.put(raise_range, x, y)
        raise_range.set_name("raise_range")
        self.widgets[raise_range.get_name()] = raise_range
        #self.glade.get_widget("game_window").show_all()
            
    def get_widget(self, name):
        if self.widgets.has_key(name):
            return self.widgets[name]
        return self.glade.get_widget(name)

    def relative_file(self, file):
        return self.glade.relative_file(file)

    def signal_autoconnect(self, instance):
        return self.glade.signal_autoconnect(instance)

class GameWindowGladeTest(unittest.TestCase):
    def test_getWidget(self):
	glade = GameWindowGlade()
	seat = 1
	name = glade.get_widget("name_seat%d" % seat)
	name.set_label("proppy")
        money = glade.get_widget("money_seat%d" % seat)
        money.set_label("$100")
        bet = glade.get_widget("bet_seat%d" % seat)
        bet.set_label("$100")
        cards = map(lambda x: glade.get_widget("card%d_seat%d" % ( x, seat )), xrange(1,8))
	cards[0].set_from_file("Kspades.png")
	toplevel = glade.get_widget("game_toplevel")
        board = map(lambda x: glade.get_widget("board%d" % x), xrange(1,6))
	board[0].set_from_file("Kspades.png")
        pots = map(lambda x: glade.get_widget("pot%d" % x), xrange(9))
	pots[0].set_label("$100")
        dealer_buttons = map(lambda x: glade.get_widget("dealer%d" % x), xrange(10))
        winners = map(lambda x: glade.get_widget("winner%d" % x), xrange(9))
	winners[0].set_label("hi card")
        seats = map(lambda x: glade.get_widget("sit_seat%d" % x), xrange(10))
	seats[0].show()
	seats[0].hide()
        self.table_status = glade.get_widget("table_status").get_buffer()
        self.table_status.set_text("\n".join(("salut", "les", "aminches")))
	fixed = glade.get_widget("game_fixed")
	children = fixed.get_children()
	self.assert_(len(children) > 0)
        quit = glade.get_widget("quit")
	quit.hide()
	quit.show()
        rebuy = glade.get_widget("rebuy")
	rebuy.hide()
	rebuy.show()
	glade.get_widget("raise_increase").show() # 1x1 button used for accelerators
        glade.get_widget("raise_decrease").show() # 1x1 button used for accelerators
        glade.get_widget("raise_increase_bb").show() # 1x1 button used for accelerators
        glade.get_widget("raise_decrease_bb").show() # 1x1 button used for accelerators
        glade.get_widget("raise_pot").show() # 1x1 button used for accelerators
        glade.get_widget("raise_half_pot").show() # 1x1 button used for accelerators
	call = glade.get_widget("call")
        call.hide()
	raise_ = glade.get_widget("raise")
        raise_.hide()
	raise_range = glade.get_widget("raise_range")
        raise_range.hide()
	check = glade.get_widget("check")
        check.hide()
	fold = glade.get_widget("fold")
        fold.hide()
	glade.relative_file("")
	glade.get_widget("switch")
	glade.signal_autoconnect(self)

	screen = glade.get_widget("game_fixed")
	widget_pots = []
        for pot in map(lambda x: glade.get_widget("pot%d" % x), xrange(9)):
            widget_pots.append((pot, screen.child_get_property(pot, "x"), screen.child_get_property(pot, "y")))
        for bet in map(lambda x: glade.get_widget("bet_seat%d" % x), xrange(10)):
            widget_pots.append((bet, screen.child_get_property(bet, "x"), screen.child_get_property(bet, "y")))
        for name in map(lambda x: glade.get_widget("name_seat%d" % x), xrange(10)):
            widget_pots.append((name, screen.child_get_property(name, "x"), screen.child_get_property(name, "y")))

class SignalHandler:
    def on_sit_seat0_clicked(self, widget):
        print "on_sit_seat0_clicked"
    def on_game_background_clicked(self, widget):
        print "on_game_background_clicked"

if __name__ == '__main__':
    #unittest.main()
    glade = GameWindowGlade()
    handler = SignalHandler()
    glade.signal_autoconnect(handler)
    gtk.rc_parse("data/skin/mockup.gtkrc")
    window = gtk.Window()
    event = glade.get_widget("game_window")
    name_seat = glade.get_widget("name_seat0")
    name_seat.set_label("proppy")
    fixed = glade.get_widget("game_fixed")
    fixed.remove(name_seat)
    fixed.put(name_seat, 100, 100)
    window.add(event)
    window.set_resizable(False)
    window.set_size_request(800, 600)
    window.show_all()
    gtk.main()

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
    def __init__(self, glade_file):
        self.widgets = {}
        self.glade = gtk.glade.XML(glade_file)
        window = self.glade.get_widget('game_window')
        fixed = self.glade.get_widget('game_fixed')
        window.remove(fixed)
        event = gtk.EventBox()
        event.set_name("game_window")
        self.widgets[event.get_name()] = event
        event.add(fixed)
        for seat_index in xrange(0, 10):
            seat = self.glade.get_widget('sit_seat%d' % seat_index)
            (x, y) = (fixed.child_get_property(seat, 'x'), fixed.child_get_property(seat, 'y'))
            for card_index in xrange(1, 8):
                image = gtk.Image()
                image.set_name("card%d_seat%d" % (card_index, seat_index))
                fixed.put(image, x+(card_index-1)*10, y+20)
                self.widgets[image.get_name()] = image
        for board_index in xrange(1, 6):
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
        for winner_index in xrange(4):
            winner = gtk.Label()
            winner.set_name('winner%d' % winner_index)
            self.widgets[winner.get_name()] = winner
            fixed.put(winner, x, y - winner_index*10)
        winner_down = self.glade.get_widget('winner1')
        (x, y) = (fixed.child_get_property(winner_down, 'x'), fixed.child_get_property(winner_down, 'y'))
        fixed.remove(winner_down)
        for winner_index in xrange(4, 9):
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
        def button2hscale(button):
            hscale = gtk.HScale()
            hscale.set_name(button.get_name())
            self.widgets[hscale.get_name()] = hscale
            x = fixed.child_get_property(button, 'x')
            y = fixed.child_get_property(button, 'y')
            hscale.set_size_request(*button.size_request())
            fixed.remove(button)
            fixed.put(hscale, x, y)
        button2hscale(self.glade.get_widget("raise_range"))
        names = map(lambda seat: self.glade.get_widget("name_seat%d" % seat), xrange(10))
        def button2label(button):
            label = gtk.Label()
            label.set_name(button.get_name())
            self.widgets[label.get_name()] = label
            x = fixed.child_get_property(button, 'x')
            y = fixed.child_get_property(button, 'y')
            fixed.remove(button)
            fixed.put(label, x, y)
        map(button2label, names)
        moneys = map(lambda seat: self.glade.get_widget("money_seat%d" % seat), xrange(10))
        map(button2label, moneys)
        self.glade.get_widget("game_fixed").show_all()
            
    def get_widget(self, name):
        if self.widgets.has_key(name):
            return self.widgets[name]
        return self.glade.get_widget(name)

    def relative_file(self, file):
        return self.glade.relative_file(file)

    def signal_autoconnect(self, instance):
        return self.glade.signal_autoconnect(instance)

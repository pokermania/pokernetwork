# -*- mode: python -*-
#
# Copyright (C) 2006 Mekensleep <licensing@mekensleep.com>
#                    24 rue vieille du temple, 75004 Paris
#
# This software's license gives you freedom; you can copy, convey,
# propagate, redistribute and/or modify this program under the terms of
# the GNU Affero General Public License (AGPL) as published by the Free
# Software Foundation (FSF), either version 3 of the License, or (at your
# option) any later version of the AGPL published by the FSF.
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
#  Johan Euphrosine <johan@mekensleep.com>
#

import gtk
import unittest

class GameWindowGlade:
    def __init__(self, glade):
        self.widgets = {}
        self.glade = glade
        window = self.glade.get_widget('game_window')
        fixed = self.glade.get_widget('game_window_fixed')
        window.remove(fixed)
        event = gtk.EventBox()
        event.set_name("game_window")
        self.widgets[event.get_name()] = event
        event.add(fixed)
        for seat_index in xrange(0, 10):
            for card_index in xrange(1, 8):
                def button2image(button):
                    image = gtk.Image()
                    image.set_name(button.get_name())
                    self.widgets[image.get_name()] = image
                    x = fixed.child_get_property(button, 'x')
                    y = fixed.child_get_property(button, 'y')
                    fixed.remove(button)
                    fixed.put(image, x, y)
                button2image(self.get_widget("card%d_seat%d" % (card_index, seat_index)))
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
        def button2textview(button):            
            table_status = gtk.TextView()
            table_status.set_name(button.get_name())
            self.widgets[table_status.get_name()] = table_status
            x = fixed.child_get_property(button, 'x')
            y = fixed.child_get_property(button, 'y')
            fixed.remove(button)
            fixed.put(table_status, x, y)
            return table_status
        button2textview(self.glade.get_widget("table_status"))
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
            fixed.remove(button)
            hscale.set_size_request(*button.get_size_request())
            fixed.put(hscale, x, y)
            return hscale
        hscale = button2hscale(self.glade.get_widget("raise_range"))
        names = map(lambda seat: self.glade.get_widget("name_seat%d" % seat), xrange(10))
        def button2label(button):
            label = gtk.Label()
            label.set_name(button.get_name())
            self.widgets[label.get_name()] = label
            x = fixed.child_get_property(button, 'x')
            y = fixed.child_get_property(button, 'y')
            fixed.remove(button)
            fixed.put(label, x, y)
            return label
        map(button2label, names)
        moneys = map(lambda seat: self.glade.get_widget("money_seat%d" % seat), xrange(10))
        map(button2label, moneys)
        actions_name = ("raise", "check", "fold", "call")
        actions = map(self.glade.get_widget, actions_name)
        def button2toggle(button):
            toggle = gtk.ToggleButton()
            toggle.set_name(button.get_name())
            toggle.set_size_request(*button.get_size_request())
            self.widgets[toggle.get_name()] = toggle
            x = fixed.child_get_property(button, 'x')
            y = fixed.child_get_property(button, 'y')
            fixed.remove(button)
            fixed.put(toggle, x, y)
            return toggle
        map(button2toggle, actions)
        self.glade.get_widget("game_window_fixed").show_all()
            
    def get_widget(self, name):
        if self.widgets.has_key(name):
            return self.widgets[name]
        return self.glade.get_widget(name)

    def relative_file(self, file):
        return self.glade.relative_file(file)

    def signal_autoconnect(self, instance):
        for name, widget in self.widgets.iteritems():
            method = getattr(instance, "on_%s_clicked" % name, None)
            if method: widget.connect("clicked", method)

if __name__ == '__main__':
    glade = GameWindowGlade('data/interface/table/mockup.glade')
    event_box = glade.get_widget('game_window')
    window = gtk.Window()
    window.add(event_box)
    gtk.rc_parse('data/interface/table/gtkrc')
    for seat_index in xrange(0, 10):
        for card_index in xrange(1, 8):
            glade.get_widget("card%d_seat%d" % (card_index, seat_index)).set_from_file('data/interface/table/card_back.png')
    window.show_all()
    gtk.main()

# Interpreted by emacs
# Local Variables:
# compile-command: "/usr/bin/python gamewindow.py"
# End:


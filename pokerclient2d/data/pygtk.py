#!/usr/bin/python
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
# the Free Software Foundation; either version 3 of the License, or
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
if __name__ == '__main__':
    gtk.rc_parse("interface/table/gtkrc")
    glade = gtk.glade.XML('interface/table/mockup.glade')
    window = glade.get_widget('game_window')
    window.show_all()
    gtk.main()

# Interpreted by emacs
# Local Variables:
# compile-command: "make interface/table/gtkrc.mockup interface/table/mockup.glade && /usr/bin/python pygtk.py"
# End:

#
# Copyright (C) 2005, 2006 Mekensleep
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
#  Johan Euphrosine <proppy@aminche.com>
#

import unittest
import gladegen

class GladeGenTest(unittest.TestCase):
    def test(self):
	glade_string = gladegen.glade_interface('bodyTest')
	self.assertEquals('<glade-interface>bodyTest</glade-interface>', glade_string)
	glade_string = gladegen.glade_child('bodyTest')
	self.assertEquals('<child>bodyTest</child>', glade_string)
	glade_string = gladegen.glade_widget('classTest', 'idTest', 'bodyTest')
	self.assertEquals('<widget class="classTest" id="idTest">bodyTest</widget>', glade_string)
	glade_string = gladegen.glade_property('nameTest', 'bodyTest')
	self.assertEquals('<property name="nameTest">bodyTest</property>', glade_string)
	glade_string = gladegen.glade_signal('nameTest', 'handlerTest')
	self.assertEquals('<signal name="nameTest" handler="handlerTest"/>', glade_string)
	glade_string = gladegen.glade_packing('bodyTest')
	self.assertEquals('<packing>bodyTest</packing>', glade_string)
	rc_string = gladegen.rc_style('nameTest', 'bodyTest')
	self.assertEquals('style "nameTest_style" {bodyTest}', rc_string)
	rc_string = gladegen.rc_engine('nameTest', 'bodyTest')
	self.assertEquals('engine "nameTest" {bodyTest}', rc_string)
	rc_string = gladegen.rc_image('fileTest')
	self.assertEquals('image {function = BOX file = "fileTest"}', rc_string)
	rc_string = gladegen.rc_widget('nameTest')
	self.assertEquals('widget "*nameTest" style "nameTest_style"', rc_string)

if __name__ == '__main__':
    unittest.main()

# Interpreted by emacs
# Local Variables:
# compile-command: "( python test-gladegen.py )"
# End:

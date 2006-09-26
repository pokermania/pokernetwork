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
#  Loic Dachary <loic@gnu.org>
#
# Build a khotkeys (KDE) file from the key binding
# specifications of poker2d.xml.in
#
from pokerengine.pokerengineconfig import Config

poker2d_title = "Poker"

settings = Config(['.'])
import os
srcdir = os.environ['srcdir']
if srcdir == None or srcdir == "": srcdir = "."
settings.load(srcdir + '/' + 'poker2d.xml.in')

keys = settings.headerGetProperties('/settings/keys/key')

print """
[Data]
DataCount=1

[Data_1]
Comment=poker2d desktop wide key bindings forwarded to the poker2d window key bindings http://freshmeat.net/projects/poker-network/
DataCount=""" + str(len(keys)) + """
Enabled=false
Name=poker2d
SystemGroup=0
Type=ACTION_DATA_GROUP

[Data_1Conditions]
Comment=
ConditionsCount=0
"""

index=1
for key in keys:
    if not key.has_key('khotkeys_output'):
        continue
    print """
[Data_1_""" + str(index) + """]
Comment=""" + key['comment'] + """
Enabled=true
Name=""" + key['name'] + """
Type=KEYBOARD_INPUT_SHORTCUT_ACTION_DATA

[Data_1_""" + str(index) + """Actions]
ActionsCount=1

[Data_1_""" + str(index) + """Actions0]
ActiveWindow=false
Input=""" + key['khotkeys_output'] + """
IsDestinationWindow=true
Type=KEYBOARD_INPUT

[Data_1_""" + str(index) + """Actions0DestinationWindow]
Comment=Poker2d Window
WindowsCount=1

[Data_1_""" + str(index) + """Actions0DestinationWindow0]
Class=
ClassType=0
Comment=Poker
Role=
RoleType=0
Title=""" + poker2d_title + """
TitleType=2
Type=SIMPLE
WindowTypes=1

[Data_1_""" + str(index) + """Conditions]
Comment=
ConditionsCount=0

[Data_1_""" + str(index) + """Triggers]
Comment=Simple_action
TriggersCount=1

[Data_1_""" + str(index) + """Triggers0]
Key=""" + key['khotkeys_input'] + """
Type=SHORTCUT

"""
    index += 1

print """
[Main]
Autostart=true
Disabled=false
Version=2
ImportId=poker2d
"""

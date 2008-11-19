# Copyright (C) 2006 Mekensleep <licensing@mekensleep.com>
#                    24 rue vieille du temple, 75004 Paris
#
# This software's license gives you freedom; you can copy, convey,
# propogate, redistribute and/or modify this program under the terms of
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

#
# Copyright (C) 2006, 2007, 2008, 2009 Loic Dachary <loic@dachary.org>
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
#  Loic Dachary <loic@dachary.org>
#  Hannes Uebelacker <hannes@pokermania.de>
#
import os
import logging
from collections import namedtuple

Message = namedtuple('Message', ['severity', 'path', 'refs', 'message', 'args', 'formated'])
messages_out = [] # a list of Message items

class TestLoggingHandler(logging.Handler):
    def __init__(self):
        logging.Handler.__init__(self)

    def emit(self, record):
        messages_out.append(Message(
            severity = record.levelno,
            path = record.name,
            refs = record.refs if hasattr(record, 'refs') else '[]',
            message = record.msg,
            args = record.args,
            formated = self.format(record)
        ))

def search_output(needle):
    for message in messages_out:
        if needle in message.formated:
            return True
    return False

def clear_all_messages():
    global messages_out
    messages_out = []

def get_messages():
    return [m.formated for m in messages_out]



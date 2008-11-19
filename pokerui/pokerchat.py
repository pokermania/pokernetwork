#
# Copyright (C) 2004, 2005, 2006 Mekensleep <licensing@mekensleep.com>
#                                24 rue vieille du temple, 75004 Paris
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
#  Loic Dachary <loic@dachary.org>
#

from pokernetwork.pokerclientpackets import *

class PokerChat:
    chat2type = {
    "/win":      PACKET_POKER_PLAYER_WIN,
    "/raise":    PACKET_POKER_RAISE,
    "/check":    PACKET_POKER_CHECK,
    "/call":     PACKET_POKER_CALL,
    "/fold":     PACKET_POKER_FOLD,
    "/sit":      PACKET_POKER_SIT,
    "/sitout":   PACKET_POKER_SIT_OUT,
    "/look":     PACKET_POKER_LOOK_CARDS,
    "/arrive":   PACKET_POKER_PLAYER_ARRIVE
    }
    emoteAnimation = [
        "win"]
#        "raise",
#        "check",
#        "call",
#        "fold",
#        "sit",
#        "sitout",
#        "look",
#        "arrive"]
    
    def getFirstSmiley():
        pass
    getFirstSmiley = staticmethod(getFirstSmiley)

    
    def isChatTrigger(word):
        return PokerChat.chat2type.has_key(word)
    isChatTrigger = staticmethod(isChatTrigger)


    def getChatType(word):
        if PokerChat.isChatTrigger(word):
            return PokerChat.chat2type[word]
        return None
    getChatType = staticmethod(getChatType)
        
    def filterChatTrigger(message):
        words = message.split()
        for word in words:
            if PokerChat.isChatTrigger(word):
                message = message.replace(word, "", 1)
                return message
        return message
    filterChatTrigger = staticmethod(filterChatTrigger)

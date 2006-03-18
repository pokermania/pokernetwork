#
# Copyright (C) 2004, 2005, 2006 Mekensleep
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

from pokernetwork.pokerpackets import *

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

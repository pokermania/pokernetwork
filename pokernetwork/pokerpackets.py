#
# Copyright (C) 2004 Mekensleep
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
#  Henry Precheur <henry@precheur.org>
#  Cedric Pinson <cpinson@freesheep.org>
#

from time import strftime, gmtime

"""\
Packets exchanged between the poker server and a poker client.

When a packet is said to be "inferred" by the client, it means
that it is not sent by the server because the
client can deduce the corresponding event from the previous packets.
The pokerclient protocol hide this difference by creating events as if they
were received from the server. The distinction should only matter for
a program willing to talk directly to the server, in wich case it is safe
to assume that all packet marked as being "inferred" will not actually be received by the server. In order to keep the
complexity of writing the client to a reasonable level, the server
provides exhaustive information about the game before the beginning of
every turn. 

The "Direction:" field for each packet shows wether it travels from
the client to the server (server <= client), from the server to the
client (server => client) or both ways (server <=> client). Packets
that are never used for client / server dialog, i.e. which are
infered by the client and used internally are noted with
client <=> client.

The main pot is never refered as such and is considered to be the
pot with the largest index. If there are three pots (index 0, 1, 2),
it is safe to assume that the pot with index 2 is the main pot.

The terms table/game are used interchangeably depending on the context.

The documentation is kept terse and emphasizes the non-intuitive
behaviour associated to each packet.
"""
from struct import pack, unpack, calcsize
from pokernetwork.packets import *

########################################

PACKET_POKER_SEATS = 111
PacketNames[PACKET_POKER_SEATS] = "POKER_SEATS"

class PacketPokerSeats(Packet):
    """\
Semantics: attribution of the seats of a game to the players.

Context: packet sent at least once per turn. It is guaranteed
that no player engaged in a turn (i.e. who shows in a
PACKET_POKER_IN_GAME packet) will leave their seat before
the turn is over (i.e. before packet  PACKET_POKER_STATE packet
with string == "end" is received).
It is guaranteed that all PACKET_PLAYER_ARRIVE packets for
all players listed in the "seats" have already been sent
by the server.

Notes: The list is 10 seats long even when a game only allows 5
players to seat.

seats: list of serials of players. The list contains exactly 10 integers.
       The position of the serial of a given player is the seat number.
       A serial of 0 means the seat is empty.
       Example: [ 0, 0, 201, 0, 0, 0, 0, 0, 305, 0 ]
game_id: integer uniquely identifying a game.
"""

    type = PACKET_POKER_SEATS
    game_id = 0
    seats = []

    format = "!I"
    format_size = calcsize(format)
    format_element = "!I"

    def __init__(self, *args, **kwargs):
        if kwargs.has_key("seats"):
            self.seats = kwargs["seats"]
        if kwargs.has_key("game_id"):
            self.game_id = kwargs["game_id"]

    def pack(self):
        return Packet.pack(self) + self.packlist(self.seats, PacketPokerSeats.format_element) + pack(PacketPokerSeats.format, self.game_id)
        
    def unpack(self, block):
        block = Packet.unpack(self, block)
        (block, self.seats) = self.unpacklist(block, PacketPokerSeats.format_element)
        (self.game_id,) = unpack(PacketPokerSeats.format, block[:PacketPokerSeats.format_size])
        return block[PacketPokerSeats.format_size:]

    def calcsize(self):
        return Packet.calcsize(self) + self.calcsizelist(self.seats, PacketPokerSeats.format_element) + PacketPokerSeats.format_size

    def __str__(self):
        return Packet.__str__(self) + " game_id = %d, seats = %s" % ( self.game_id, self.seats )

PacketFactory[PACKET_POKER_SEATS] = PacketPokerSeats

########################################

PACKET_POKER_ID = 112
PacketNames[PACKET_POKER_ID] = "POKER_ID"

class PacketPokerId(PacketSerial):
    """abstract packet with game id and serial"""

    type = PACKET_POKER_ID
    game_id = 0

    format = "!I"
    format_size = calcsize(format)

    def __init__(self, *args, **kwargs):
        self.game_id = kwargs.get("game_id", 0)
        PacketSerial.__init__(self, *args, **kwargs)

    def pack(self):
        return PacketSerial.pack(self) + pack(PacketPokerId.format, self.game_id)
        
    def unpack(self, block):
        block = PacketSerial.unpack(self, block)
        (self.game_id,) = unpack(PacketPokerId.format, block[:PacketPokerId.format_size])
        return block[PacketPokerId.format_size:]

    def calcsize(self):
        return PacketSerial.calcsize(self) + PacketPokerId.format_size

    def __str__(self):
        return PacketSerial.__str__(self) + " game_id = %d" % self.game_id

PacketFactory[PACKET_POKER_ID] = PacketPokerId

########################################

PACKET_POKER_ERROR = 114
PacketNames[PACKET_POKER_ERROR] = "ERROR"

class PacketPokerError(PacketPokerId):
    """

    Packet describing an error
    
    """

    type = PACKET_POKER_ERROR
    other_type = 0
    code = 0
    message = ""

    format = "!IB"
    format_size = calcsize(format)

    def __init__(self, *args, **kwargs):
        self.message = kwargs.get("message", "no message")
        self.code = kwargs.get("code", 0)
        self.other_type = kwargs.get("other_type", PACKET_POKER_ERROR)
        PacketPokerId.__init__(self, *args, **kwargs)

    def pack(self):
        return PacketPokerId.pack(self) + self.packstring(self.message) + pack(PacketPokerError.format, self.code, self.other_type)

    def unpack(self, block):
        block = PacketPokerId.unpack(self, block)
        (block, self.message) = self.unpackstring(block)
        (self.code, self.other_type) = unpack(PacketPokerError.format, block[:PacketPokerError.format_size])
        return block[PacketPokerError.format_size:]

    def calcsize(self):
        return PacketPokerId.calcsize(self) + self.calcsizestring(self.message) + PacketPokerError.format_size

    def __str__(self):
        return PacketPokerId.__str__(self) + " message = %s, code = %d, other_type = %s" % (self.message, self.code, PacketNames[self.other_type] )

PacketFactory[PACKET_POKER_ERROR] = PacketPokerError

########################################

PACKET_POKER_POSITION = 115
PacketNames[PACKET_POKER_POSITION] = "POKER_POSITION"

class PacketPokerPosition(Packet):
    """\
Semantics: the player "serial" is now in position for game
"game_id" and should act. If "serial" is 0, no player is
in position.

Direction: server  => client

Context: emitted by the server when paying blinds or antes,
in which case the "serial" field does not contain a
serial number but a position. This packet is discarded
when other packets are inferred. Inferred by the client
during all other betting rounds.
A PACKET_POKER_POSITION with serial 0 is inferred by the
client at the end of each turn.

serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

    type = PACKET_POKER_POSITION

    format = "!IB"
    format_size = calcsize(format)

    def __init__(self, *args, **kwargs):
        self.game_id = kwargs.get("game_id", 0)
        self.position = kwargs.get("position", -1)
        self.serial = kwargs.get("serial", 0) # accepted by constructor but otherwise ignored

    def pack(self):
        return Packet.pack(self) + pack(PacketPokerPosition.format, self.game_id, self.position)
        
    def unpack(self, block):
        block = Packet.unpack(self, block)
        (self.game_id, self.position) = unpack(PacketPokerPosition.format, block[:PacketPokerPosition.format_size])
        if self.position == 255: self.position = -1
        return block[PacketPokerPosition.format_size:]

    def calcsize(self):
        return Packet.calcsize(self) + PacketPokerPosition.format_size

    def __str__(self):
        return Packet.__str__(self) + " game_id = %d, position = %d, serial = %d" % ( self.game_id, self.position, self.serial )

PacketFactory[PACKET_POKER_POSITION] = PacketPokerPosition

########################################

PACKET_POKER_BET = 116
PacketNames[PACKET_POKER_BET] = "POKER_BET"

class PacketPokerBet(PacketPokerId):
    """base class for raise"""

    type = PACKET_POKER_BET
    amount = []

    format_element = "!B"
    
    def __init__(self, *args, **kwargs):
        if kwargs.has_key("amount"):
            self.amount = kwargs["amount"]
        PacketPokerId.__init__(self, *args, **kwargs)
        
    def pack(self):
        return PacketPokerId.pack(self) + self.packlist(self.amount, PacketPokerBet.format_element)

    def unpack(self, block):
        block = PacketPokerId.unpack(self, block)
        (block, self.amount) = self.unpacklist(block, PacketPokerBet.format_element)
        return block
    
    def calcsize(self):
        return PacketPokerId.calcsize(self) + self.calcsizelist(self.amount, PacketPokerBet.format_element)

    def __str__(self):
        return PacketPokerId.__str__(self) + " amount = %s" % self.amount

PacketFactory[PACKET_POKER_BET] = PacketPokerBet

########################################

PACKET_POKER_FOLD = 118
PacketNames[PACKET_POKER_FOLD] = "POKER_FOLD"

class PacketPokerFold(PacketPokerId):
    """\
Semantics: the "serial" player folded.

Direction: server <=> client

serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

    type = PACKET_POKER_FOLD

PacketFactory[PACKET_POKER_FOLD] = PacketPokerFold

########################################

PACKET_POKER_STATE = 119
PacketNames[PACKET_POKER_STATE] = "POKER_STATE"

class PacketPokerState(PacketPokerId):
    """\
Semantics: the state of the game "game_id" changed to
"string". The common game states are:

 null : new game.
 end : a game just ended.
 blindAnte : players are paying blinds and/or antes.

The other game states are not pre-determined and depend on the content
of the variant file. For instance, the states matching the
poker.holdem.xml variant file are : pre-flop, flop, turn and river.

Direction: server  => client

Context: the sequence of states is guaranteed, i.e. "turn" will never be
sent before "flop". However, there is no guarantee that the next state
will ever be sent. For instance, if a holdem game is canceled
(i.e. PACKET_POKER_CANCELED is sent) because no player is willing to pay
the blinds, the client must know that it will never receive the
packet announcing the "pre-flop" state. The "end" state is not
sent when a game is canceled (i.e. PACKET_POKER_CANCELED is sent).

game_id: integer uniquely identifying a game.
string: state of the game.
"""

    type = PACKET_POKER_STATE
    string = ""

    def __init__(self, *args, **kwargs):
        if kwargs.has_key("string"):
            self.string = kwargs["string"]
        PacketPokerId.__init__(self, *args, **kwargs)
        
    def pack(self):
        return PacketPokerId.pack(self) + self.packstring(self.string)

    def unpack(self, block):
        block = PacketPokerId.unpack(self, block)
        (block, self.string) = self.unpackstring(block)
        return block
    
    def calcsize(self):
        return PacketPokerId.calcsize(self) + self.calcsizestring(self.string)

    def __str__(self):
        return PacketPokerId.__str__(self) + " string = %s" % self.string


PacketFactory[PACKET_POKER_STATE] = PacketPokerState

########################################

PACKET_POKER_WIN = 120
PacketNames[PACKET_POKER_WIN] = "POKER_WIN"

class PacketPokerWin(PacketPokerId):
    """\
Semantics: the "serials" of the players who won
the turn for game "game_id" to display the showdown.

Context: this packet is sent even when there is no showdown, i.e. when all
other players folded. However, it is not sent if the game is canceled
(i.e. PACKET_POKER_CANCELED is sent). It is sent after
the PACKET_POKER_STATE packet announcing the "end" state and after all
necessary information is sent to explain the
showdown (i.e. the value of the losing cards). The client may deduce
the serials of players who won from previous packets and use the
packet information for checking purposes only.

The client infers the following packets from PACKET_POKER_WIN:

PACKET_POKER_PLAYER_NO_CARDS
PACKET_POKER_BEST_CARDS
PACKET_POKER_CHIPS_POT_MERGE
PACKET_POKER_CHIPS_POT2PLAYER
PACKET_POKER_POT_CHIPS
PACKET_POKER_PLAYER_CHIPS

They roughly match the following logic. Some players mucked their
losing cards (PACKET_POKER_PLAYER_NO_CARDS). The winners show their
best five card combination (high and/or low)
PACKET_POKER_BEST_CARDS. If there are split pots and a player wins
more than one pot, merge the chips together before giving them to the
winner (PACKET_POKER_CHIPS_POT_MERGE). Give each player the part of
the pot they won (PACKET_POKER_CHIPS_POT2PLAYER): there may be more
than one packet for each player if more than one pot is involved. When
the distribution is finished all pots are empty
(PACKET_POKER_POT_CHIPS) and each player has a new amount of chips in
their stack (PACKET_POKER_PLAYER_CHIPS). These last two packets make
it possible for the client to ignore the chips movements and only deal
with the final chips amounts.

The PACKET_POKER_BEST_CARDS is only infered for actual winners. Not
for players who participated in the showdown but lost. The cards of
these losers are known from a PACKET_POKER_CARDS sent before the
PACKET_POKER_WIN.

Direction: server  => client

serials: list of serials of players who won.
game_id: integer uniquely identifying a game.
"""

    type = PACKET_POKER_WIN

    serials = []

    format_element = "!I"

    def __init__(self, *args, **kwargs):
        if kwargs.has_key("serials"):
            self.serials = kwargs["serials"]
        PacketPokerId.__init__(self, *args, **kwargs)

    def pack(self):
        block = PacketPokerId.pack(self)
        block += self.packlist(self.serials, PacketPokerWin.format_element)
        return block
    
    def unpack(self, block):
        block = PacketPokerId.unpack(self, block)
        (block, self.serials) = self.unpacklist(block, PacketPokerWin.format_element)
        return block

    def calcsize(self):
        return PacketPokerId.calcsize(self) + self.calcsizelist(self.serials, PacketPokerWin.format_element)

    def __str__(self):
        return PacketPokerId.__str__(self) + " serials = %s" % self.serials

PacketFactory[PACKET_POKER_WIN] = PacketPokerWin

########################################

PACKET_POKER_CARDS = 113
PacketNames[PACKET_POKER_CARDS] = "POKER_CARDS"

class PacketPokerCards(PacketPokerId):
    """base class for player / board / best cards"""
    type = PACKET_POKER_CARDS

    cards = []

    format_element = "!B"

    def __init__(self, *args, **kwargs):
        if kwargs.has_key("cards"):
            self.cards = kwargs["cards"]
        PacketPokerId.__init__(self, *args, **kwargs)
        
    def pack(self):
        block = PacketPokerId.pack(self)
        block += self.packlist(self.cards, PacketPokerCards.format_element)
        return block
    
    def unpack(self, block):
        block = PacketPokerId.unpack(self, block)
        (block, self.cards) = self.unpacklist(block, PacketPokerCards.format_element)
        return block

    def calcsize(self):
        return PacketPokerId.calcsize(self) + self.calcsizelist(self.cards, PacketPokerCards.format_element)

    def __str__(self):
        return PacketPokerId.__str__(self) + " cards = %s" % self.cards
    
PacketFactory[PACKET_POKER_CARDS] = PacketPokerCards

########################################

PACKET_POKER_PLAYER_CARDS = 122
PacketNames[PACKET_POKER_PLAYER_CARDS] = "POKER_PLAYER_CARDS"

class PacketPokerPlayerCards(PacketPokerCards):
    """\
Semantics: the ordered list of "cards" for player "serial"
in game "game_id".

Direction: server  => client

cards: list of integers describing cards.
       255 == placeholder, i.e. down card with unknown value
       bit 7 and bit 8 set == down card
       bit 7 and bit 8 not set == up card
       bits 1 to 6 == card value as follows:

       2h/00  2d/13  2c/26  2s/39
       3h/01  3d/14  3c/27  3s/40
       4h/02  4d/15  4c/28  4s/41
       5h/03  5d/16  5c/29  5s/42
       6h/04  6d/17  6c/30  6s/43
       7h/05  7d/18  7c/31  7s/44
       8h/06  8d/19  8c/32  8s/45
       9h/07  9d/20  9c/33  9s/46
       Th/08  Td/21  Tc/34  Ts/47
       Jh/09  Jd/22  Jc/35  Js/48
       Qh/10  Qd/23  Qc/36  Qs/49
       Kh/11  Kd/24  Kc/37  Ks/50
       Ah/12  Ad/25  Ac/38  As/51
       
serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

    type = PACKET_POKER_PLAYER_CARDS

PacketFactory[PACKET_POKER_PLAYER_CARDS] = PacketPokerPlayerCards

########################################

PACKET_POKER_BOARD_CARDS = 123
PacketNames[PACKET_POKER_BOARD_CARDS] = "POKER_BOARD_CARDS"

class PacketPokerBoardCards(PacketPokerCards):
    """\
Semantics: the ordered list of community "cards" 
for game "game_id".

Direction: server  => client

cards: list of integers describing cards.
       255 == placeholder, i.e. down card with unknown value
       bit 7 and bit 8 set == down card
       bit 7 and bit 8 not set == up card
       bits 1 to 6 == card value as follows:

       2h/00  2d/13  2c/26  2s/39
       3h/01  3d/14  3c/27  3s/40
       4h/02  4d/15  4c/28  4s/41
       5h/03  5d/16  5c/29  5s/42
       6h/04  6d/17  6c/30  6s/43
       7h/05  7d/18  7c/31  7s/44
       8h/06  8d/19  8c/32  8s/45
       9h/07  9d/20  9c/33  9s/46
       Th/08  Td/21  Tc/34  Ts/47
       Jh/09  Jd/22  Jc/35  Js/48
       Qh/10  Qd/23  Qc/36  Qs/49
       Kh/11  Kd/24  Kc/37  Ks/50
       Ah/12  Ad/25  Ac/38  As/51
       
game_id: integer uniquely identifying a game.
"""

    type = PACKET_POKER_BOARD_CARDS

PacketFactory[PACKET_POKER_BOARD_CARDS] = PacketPokerBoardCards

########################################

PACKET_POKER_BEST_CARDS = 135
PacketNames[PACKET_POKER_BEST_CARDS] = "POKER_BEST_CARDS"

class PacketPokerBestCards(PacketPokerCards):
    """\
Semantics: ordered list  of five "bestcards" hand for
player "serial" in game "game_id" that won the "side"
side of the pot. The "board", if not empty, is the list
of community cards at showdown. Also provides the
"cards" of the player.

Direction: client <=> client

cards: list of integers describing the player cards:

       2h/00  2d/13  2c/26  2s/39
       3h/01  3d/14  3c/27  3s/40
       4h/02  4d/15  4c/28  4s/41
       5h/03  5d/16  5c/29  5s/42
       6h/04  6d/17  6c/30  6s/43
       7h/05  7d/18  7c/31  7s/44
       8h/06  8d/19  8c/32  8s/45
       9h/07  9d/20  9c/33  9s/46
       Th/08  Td/21  Tc/34  Ts/47
       Jh/09  Jd/22  Jc/35  Js/48
       Qh/10  Qd/23  Qc/36  Qs/49
       Kh/11  Kd/24  Kc/37  Ks/50
       Ah/12  Ad/25  Ac/38  As/51
       
bestcards: list of integers describing the winning combination cards:
board: list of integers describing the community cards:
hand: readable string of the name best hand
       
serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

    type = PACKET_POKER_BEST_CARDS

    def __init__(self, *args, **kwargs):
        self.side = kwargs.get("side", "")
        self.hand = kwargs.get("hand", "")
        self.bestcards = kwargs.get("bestcards", [])
        self.board = kwargs.get("board", [])
        PacketPokerCards.__init__(self, *args, **kwargs)
        
    def __str__(self):
        return PacketPokerCards.__str__(self) + " side = %s, hand = %s, bestcards = %s, board = %s" % ( self.side, self.hand, str(self.bestcards), str(self.board) )

PacketFactory[PACKET_POKER_BEST_CARDS] = PacketPokerBestCards

########################################

PACKET_POKER_CHIPS = 117
PacketNames[PACKET_POKER_CHIPS] = "POKER_CHIPS"

class PacketPokerChips(PacketPokerId):
    """base class"""

    type = PACKET_POKER_CHIPS

    empty = [0,0,0,0,0,0]

    bet = empty[:]

    format_element = "!B"

    def __init__(self, *args, **kwargs):
        if kwargs.has_key("bet"):
            self.bet = kwargs["bet"]
        PacketPokerId.__init__(self, *args, **kwargs)

    def pack(self):
        block = PacketPokerId.pack(self)
        block += self.packlist(self.bet, PacketPokerChips.format_element)
        return block

    def unpack(self, block):
        block = PacketPokerId.unpack(self, block)
        (block, self.bet) = self.unpacklist(block, PacketPokerChips.format_element)
        return block

    def calcsize(self):
        return PacketPokerId.calcsize(self) + self.calcsizelist(self.bet, PacketPokerChips.format_element) 

    def __str__(self):
        return PacketPokerId.__str__(self) + " bet = %s" % ( self.bet )

PacketFactory[PACKET_POKER_CHIPS] = PacketPokerChips

########################################

PACKET_POKER_PLAYER_CHIPS = 124
PacketNames[PACKET_POKER_PLAYER_CHIPS] = "POKER_PLAYER_CHIPS"

class PacketPokerPlayerChips(PacketPokerChips):
    """\
Semantics: the "money" of the player "serial" engaged in
game "game_id" and the "bet" currently wagered by the player, if any.

Direction: server  => client

Context: this packet is infered each time the bet or the chip
stack of a player is modified.

Notes: the server formats the chip list according to the
/bet/chips element of the betting structure description.
For instance if the poker.10-15-pot-limit.xml betting structure
description contains:

    <chips values="5 10 20 25 50 100 250 500 5000" />

then a "bet" field containing [1, 0, 2, 0, 1, 0, 0, 0, 0]
means one chips of 5, two chips of 20 and one chip of 50.
In order to avoid the complexity of refering to the proper
betting structure, the may normalize the lists so as to
behave as if all betting structure had the following
/bet/chips element:

    <chips values="1 2 5 10 20 25 50 100 250 500 1000 2000 5000" />


bet: list of integers counting the number of chips wagered by
     the player for the current betting round. The value of each
     chip depends on the betting structure as explained above.
money: list of integers counting the number of chips available
     to the player for this game. The value of each
     chip depends on the betting structure as explained above.
serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

    type = PACKET_POKER_PLAYER_CHIPS

    empty = [0,0,0,0,0,0]

    money = empty[:]

    format_element = "!B"

    def __init__(self, *args, **kwargs):
        if kwargs.has_key("money"):
            self.money = kwargs["money"]
        PacketPokerChips.__init__(self, *args, **kwargs)

    def pack(self):
        block = PacketPokerChips.pack(self)
        block += self.packlist(self.money, PacketPokerPlayerChips.format_element)
        return block

    def unpack(self, block):
        block = PacketPokerChips.unpack(self, block)
        (block, self.money) = self.unpacklist(block, PacketPokerPlayerChips.format_element)
        return block

    def calcsize(self):
        return PacketPokerChips.calcsize(self) + self.calcsizelist(self.money, PacketPokerPlayerChips.format_element)

    def __str__(self):
        return PacketPokerChips.__str__(self) + " money = %s" % ( self.money )

PacketFactory[PACKET_POKER_PLAYER_CHIPS] = PacketPokerPlayerChips

########################################

PACKET_POKER_POT_CHIPS = 125
PacketNames[PACKET_POKER_POT_CHIPS] = "POKER_POT_CHIPS"

class PacketPokerPotChips(PacketPokerChips):
    """\
Semantics: the "bet" put in the "index" pot of the "game_id" game.

Direction: server  => client

Context: this packet is sent at least each time the pot "index" is
updated.

bet: list of pairs ( chip_value, chip_count ).
index: integer uniquely identifying a side pot in the range [0,10[
game_id: integer uniquely identifying a game.
"""

    type = PACKET_POKER_POT_CHIPS

    index = 0

    format = "!B"
    format_size = calcsize(format)

    def __init__(self, *args, **kwargs):
        if kwargs.has_key("index"):
            self.index = kwargs["index"]
        PacketPokerChips.__init__(self, *args, **kwargs)

    def pack(self):
        return PacketPokerChips.pack(self) + pack(PacketPokerChips.format, self.index)

    def unpack(self, block):
        block = PacketPokerChips.unpack(self, block)
        (self.index,) = unpack(PacketPokerPotChips.format, block[:PacketPokerPotChips.format_size])
        return block[PacketPokerStart.format_size:]

    def calcsize(self):
        return PacketPokerChips.calcsize(self) + PacketPokerPotChips.format_size

    def __str__(self):
        return PacketPokerChips.__str__(self) + " index = %d" % ( self.index )

PacketFactory[PACKET_POKER_POT_CHIPS] = PacketPokerPotChips

########################################

PACKET_POKER_CHECK = 126
PacketNames[PACKET_POKER_CHECK] = "POKER_CHECK"

class PacketPokerCheck(PacketPokerId):
    """\
Semantics: the "serial" player checked in game
"game_id".

Direction: server <=> client

serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

    type = PACKET_POKER_CHECK

PacketFactory[PACKET_POKER_CHECK] = PacketPokerCheck

########################################

PACKET_POKER_START = 127
PacketNames[PACKET_POKER_START] = "POKER_START"

class PacketPokerStart(PacketPokerId):
    """\
Semantics: start the hand "hand_serial" for game "game_id". If
"level" is greater than zero, play at tournament level "level".
If "level" is greater than zero, meaning that the hand is part
of a tournament, the fields "hands_count" is set to the number
of hands since the beginning of the tournament and "time" is set to
the number of seconds since the beginning of the
tournament.

Direction: server  => client

Context: this packet is sent exactly once per turn, after the
PACKET_POKER_DEALER and PACKET_POKER_IN_GAME packets relevant to
the hand to come.
A PACKET_POKER_CHIPS_POT_RESET packet is inferred after this packet.
A PACKET_POKER_PLAYER_CHIPS packet is inferred for each player sit after
this packet.

hands_count: total number of hands dealt for this game.
time: number of seconds since the first hand dealt for this game.
hand_serial: server wide unique identifier of this hand.
level: integer indicating the tournament level at which the current
       hand is played.
game_id: integer uniquely identifying a game.
"""

    type = PACKET_POKER_START
    hands_count = 0
    time = 0
    hand_serial = 0
    level = 0
    format = "!IIIB"
    format_size = calcsize(format)

    def __init__(self, *args, **kwargs):
        if kwargs.has_key("hands_count"):
            self.hands_count = kwargs["hands_count"]
        if kwargs.has_key("time"):
            self.time = kwargs["time"]
        if kwargs.has_key("hand_serial"):
            self.hand_serial = kwargs["hand_serial"]
        if kwargs.has_key("level"):
            self.level = kwargs["level"]
        PacketPokerId.__init__(self, *args, **kwargs)

    def pack(self):
        return PacketPokerId.pack(self) + pack(PacketPokerStart.format, self.hands_count, self.time, self.hand_serial, self.level)

    def unpack(self, block):
        block = PacketPokerId.unpack(self, block)
        (self.hands_count, self.time, self.hand_serial, self.level) = unpack(PacketPokerStart.format, block[:PacketPokerStart.format_size])
        return block[PacketPokerStart.format_size:]

    def calcsize(self):
        return PacketPokerId.calcsize(self) + PacketPokerStart.format_size

    def __str__(self):
        return PacketPokerId.__str__(self) + " hands_count = %d, time = %d, hand_serial = %d, level = %d" % (self.hands_count, self.time, self.hand_serial, self.level)

PacketFactory[PACKET_POKER_START] = PacketPokerStart

########################################

PACKET_POKER_IN_GAME = 128
PacketNames[PACKET_POKER_IN_GAME] = "POKER_IN_GAME"

class PacketPokerInGame(PacketPokerId):
    """\
Semantics: the list of "players" serials who are participating
in the hand to come or the current hand for the game "game_id".

Context: this packet is sent before the hand starts (i.e. before
the PACKET_POKER_START packet is sent). It may also be sent before
the end of the "blindAnte" round (i.e. before a PACKET_POKER_STATE
packet changing the state "blindAnte" to something else is sent).
The later case happen when a player refuses to pay the blind or
the ante. When the hand is running and is past the "blindAnte" round,
no PACKET_POKER_IN_GAME packet is sent.

players: list of serials of players participating in the hand.
game_id: integer uniquely identifying a game.
"""

    type = PACKET_POKER_IN_GAME
    players = []

    format_element = "!I"

    def __init__(self, *args, **kwargs):
        if kwargs.has_key("players"):
            self.players = kwargs["players"]
        PacketPokerId.__init__(self, *args, **kwargs)

    def pack(self):
        return PacketPokerId.pack(self) + self.packlist(self.players, PacketPokerInGame.format_element)
        
    def unpack(self, block):
        block = PacketPokerId.unpack(self, block)
        (block, self.players) = self.unpacklist(block, PacketPokerInGame.format_element)
        return block

    def calcsize(self):
        return PacketPokerId.calcsize(self) + self.calcsizelist(self.players, PacketPokerInGame.format_element)

    def __str__(self):
        return PacketPokerId.__str__(self) + " players = %s" % self.players

PacketFactory[PACKET_POKER_IN_GAME] = PacketPokerInGame

########################################

PACKET_POKER_CALL = 129
PacketNames[PACKET_POKER_CALL] = "POKER_CALL"

class PacketPokerCall(PacketPokerId):
    """\
Semantics: the "serial" player called in game "game_id".

Direction: server <=> client

serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""
    
    type = PACKET_POKER_CALL

PacketFactory[PACKET_POKER_CALL] = PacketPokerCall

########################################

PACKET_POKER_RAISE = 130
PacketNames[PACKET_POKER_RAISE] = "POKER_RAISE"

class PacketPokerRaise(PacketPokerBet):
    """\
Semantics: the "serial" player raised "bet" chips in
game "game_id".

Direction: server <=> client

Context: the client infers a PACKET_POKER_BET_LIMIT packet each
time the position changes.

Notes: the server formats the chip list according to the
/bet/chips element of the betting structure description.
For instance if the poker.10-15-pot-limit.xml betting structure
description contains:

    <chips values="5 10 20 25 50 100 250 500 5000" />

then a "bet" field containing [1, 0, 2, 0, 1, 0, 0, 0, 0]
means one chips of 5, two chips of 20 and one chip of 50.
In order to avoid the complexity of refering to the proper
betting structure, the may normalize the lists so as to
behave as if all betting structure had the following
/bet/chips element:

    <chips values="1 2 5 10 20 25 50 100 250 500 1000 2000 5000" />

bet: list of integers counting the number of chips for
     the raise. A value of all 0 means the lowest possible raise.
     A value larger than the maximum raise will be clamped by
     the server.
     The value of each chip depends on the betting structure
     as explained above.
serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""
    
    type = PACKET_POKER_RAISE

PacketFactory[PACKET_POKER_RAISE] = PacketPokerRaise

########################################

PACKET_POKER_CLIENT_ACTION = 131
PacketNames[PACKET_POKER_CLIENT_ACTION] = "POKER_CLIENT_ACTION"

class PacketPokerClientAction(PacketPokerId):
    """

    The action available/not available to the player
    
    """

    type = PACKET_POKER_CLIENT_ACTION
    display = 0
    action = ""
    format = "!B"
    format_size = calcsize(format)

    def __init__(self, *args, **kwargs):
        if kwargs.has_key("display"):
            self.display = kwargs["display"]
        if kwargs.has_key("action"):
            self.action = kwargs["action"]
        PacketPokerId.__init__(self, *args, **kwargs)
        
    def pack(self):
        return PacketPokerId.pack(self) + pack(PacketPokerClientAction.format, self.display) + self.packstring(self.action)

    def unpack(self, block):
        block = PacketPokerId.unpack(self, block)
        (self.display,) = unpack(PacketPokerClientAction.format, block[:PacketPokerClientAction.format_size])
        block = block[PacketPokerClientAction.format_size:]
        (block, self.action) = self.unpackstring(block)
        return block

    def calcsize(self):
        return PacketPokerId.calcsize(self) + PacketPokerClientAction.format_size + self.calcsizestring(self.action)

    def __str__(self):
        return PacketPokerId.__str__(self) + " display = %d, action = %s" % ( self.display, self.action )

PacketFactory[PACKET_POKER_CLIENT_ACTION] = PacketPokerClientAction

########################################

PACKET_POKER_DEALER = 134
PacketNames[PACKET_POKER_DEALER] = "POKER_DEALER"

class PacketPokerDealer(Packet):
    """\
Semantics: the dealer button for game "game_id" is at seat "dealer".
and the previous dealer was at seat "previous_dealer"

Direction: server  => client

Context: this packet is guaranteed to be sent when the game is not
running. The dealer is never altered while the game is running.
It is never sent for non button games such as stud 7.

dealer: the seat number on wich the dealer button is located [0-9].
previous_dealer: the seat number on wich the previous dealer button is located [0-9].
game_id: integer uniquely identifying a game.
"""
    
    type = PACKET_POKER_DEALER

    format = "!IBB"
    format_size = calcsize(format)

    def __init__(self, *args, **kwargs):
        self.game_id = kwargs.get("game_id", 0)
        self.dealer = kwargs.get("dealer", -1)
        self.previous_dealer = kwargs.get("previous_dealer", -1)

    def pack(self):
        return Packet.pack(self) + pack(PacketPokerDealer.format, self.game_id, self.dealer, self.previous_dealer)
        
    def unpack(self, block):
        block = Packet.unpack(self, block)
        (self.game_id, self.dealer, self.previous_dealer) = unpack(PacketPokerDealer.format, block[:PacketPokerDealer.format_size])
        if self.dealer == 255: self.dealer = -1
        if self.previous_dealer == 255: self.previous_dealer = -1
        return block[PacketPokerDealer.format_size:]

    def calcsize(self):
        return Packet.calcsize(self) + PacketPokerDealer.format_size

    def __str__(self):
        return Packet.__str__(self) + " game_id = %d, dealer = %d, previous_dealer = %d" % ( self.game_id, self.dealer, self.previous_dealer )

PacketFactory[PACKET_POKER_DEALER] = PacketPokerDealer

########################################

PACKET_POKER_TABLE_JOIN = 137
PacketNames[PACKET_POKER_TABLE_JOIN] = "POKER_TABLE_JOIN"

class PacketPokerTableJoin(PacketPokerId):
    """\
Semantics: player "serial" wants to become an observer
of the game "game_id".

Direction: server <= client

serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

    type = PACKET_POKER_TABLE_JOIN

PacketFactory[PACKET_POKER_TABLE_JOIN] = PacketPokerTableJoin

########################################

PACKET_POKER_BET_LIMIT = 138
PacketNames[PACKET_POKER_BET_LIMIT] = "POKER_BET_LIMIT"

class PacketPokerBetLimit(PacketPokerId):
    """\
Semantics: a raise must be at least "min" and most "max".
A call means wagering an amount of "call". The suggested
step to slide between "min" and "max" is "step". The step
is guaranteed to be an integral divisor of "call". The
player would be allin for the amount "allin". The player
would match the pot if betting "pot".

Context: this packet is issued each time a position change
occurs.

Direction: client <=> client

min: the minimum amount of a raise.
max: the maximum amount of a raise.
step: a hint for sliding in the [min, max] interval.
call: the amount of a call.
allin: the amount for which the player goes allin.
pot: the amount in the pot.
game_id: integer uniquely identifying a game.
"""

    type = PACKET_POKER_BET_LIMIT
    min = 0
    max = 0
    step = 0
    call = 0
    allin = 0
    pot = 0
    format = "!IIIIII"
    format_size = calcsize(format)

    def __init__(self, *args, **kwargs):
        if kwargs.has_key("min"):
            self.min = kwargs["min"]
        if kwargs.has_key("max"):
            self.max = kwargs["max"]
        if kwargs.has_key("step"):
            self.step = kwargs["step"]
        if kwargs.has_key("call"):
            self.call = kwargs["call"]
        if kwargs.has_key("allin"):
            self.allin = kwargs["allin"]
        if kwargs.has_key("pot"):
            self.pot = kwargs["pot"]
        PacketPokerId.__init__(self, *args, **kwargs)

    def pack(self):
        return PacketPokerId.pack(self) + pack(PacketPokerBetLimit.format, self.min, self.max, self.step, self.call, self.allin, self.pot)

    def unpack(self, block):
        block = PacketPokerId.unpack(self, block)
        (self.min, self.max, self.step, self.call, self.allin, self.pot) = unpack(PacketPokerBetLimit.format, block[:PacketPokerBetLimit.format_size])
        return block[PacketPokerBetLimit.format_size:]

    def calcsize(self):
        return PacketPokerId.calcsize(self) + PacketPokerBetLimit.format_size

    def __str__(self):
        return PacketPokerId.__str__(self) + " min = %d, max = %d, step = %s, call = %s, allin = %s, pot = %s" % (self.min, self.max, self.step, self.call, self.allin, self.pot)

PacketFactory[PACKET_POKER_BET_LIMIT] = PacketPokerBetLimit

########################################
PACKET_POKER_TABLE_SELECT = 139
PacketNames[PACKET_POKER_TABLE_SELECT] = "POKER_TABLE_SELECT"

class PacketPokerTableSelect(PacketString):
    """\
Semantics: request the list of tables matching the "string" constraint.
The answer is a possibly empty PACKET_POKER_TABLE_LIST packet.

Direction: server <=  client

string: a valid SQL WHERE expression. The specials value "my"
        restricts the search to the tables in which the player id
        attached to the connection is playing. 
"""
    
    type = PACKET_POKER_TABLE_SELECT

PacketFactory[PACKET_POKER_TABLE_SELECT] = PacketPokerTableSelect

########################################
PACKET_POKER_TABLE = 140
PacketNames[PACKET_POKER_TABLE] = "POKER_TABLE"

class PacketPokerTable(Packet):
    """\
Semantics: the full description of a poker game. When sent
to the server, act as a request to create the corresponding
game. When sent by the server, describes an existing poker
game.

Direction: server <=> client

name: symbolic name of the game.
variant: base name of the variant that must match a poker.<variant>.xml
         file containing a full description of the variant.
betting_structure: base name of the betting structure that must
                   match a poker.<betting_structure>.xml file containing
                   a full description of the betting structure.
id: integer used as the unique id of the game and referred to
    with the "game_id" field in all other packets.
seats: maximum number of seats in this game.
average_pot: the average amount put in the pot in the past few minutes.
percent_flop: the average percentage of players after the flop in the past
              few minutes.
observers: the number of players who joined (as in PACKET_POKER_TABLE_JOIN)
           the table but are not seated.
waiting: the number of players in the waiting list.
timeout: the number of seconds after which a player in position is forced to
         play (by folding).
custom_money: 0 if play money table, 1 if custom money table
"""
    
    type = PACKET_POKER_TABLE
    format = "!IBIHBBHBHB"
    format_size = calcsize(format)

    def __init__(self, *args, **kwargs):
        self.name = kwargs.get("name", "noname")
        self.variant = kwargs.get("variant", "holdem")
        self.betting_structure = kwargs.get("betting_structure", "2-4-limit")
        self.id = kwargs.get("id", 0)
        self.seats = kwargs.get("seats", 10)
        self.average_pot = kwargs.get("average_pot", 0)
        self.hands_per_hour = kwargs.get("hands_per_hour", 0)
        self.percent_flop = kwargs.get("percent_flop", 0)
        self.players = kwargs.get("players", 0)
        self.observers = kwargs.get("observers", 0)
        self.waiting = kwargs.get("waiting", 0)
        self.timeout = kwargs.get("timeout", 0)
        self.custom_money = kwargs.get("custom_money", 0)

    def pack(self):
        block = Packet.pack(self)
        block += pack(PacketPokerTable.format, self.id, self.seats, self.average_pot, self.hands_per_hour, self.percent_flop, self.players, self.observers, self.waiting, self.timeout, self.custom_money)
        block += self.packstring(self.name)
        block += self.packstring(self.variant)
        block += self.packstring(self.betting_structure)
        return block

    def unpack(self, block):
        block = Packet.unpack(self, block)
        (self.id, self.seats, self.average_pot, self.hands_per_hour, self.percent_flop, self.players, self.observers, self.waiting, self.timeout, self.custom_money) = unpack(PacketPokerTable.format, block[:PacketPokerTable.format_size])
        block = block[PacketPokerTable.format_size:]
        (block, self.name) = self.unpackstring(block)
        (block, self.variant) = self.unpackstring(block)
        (block, self.betting_structure) = self.unpackstring(block)
        return block

    def calcsize(self):
        return Packet.calcsize(self) + PacketPokerTable.format_size + self.calcsizestring(self.name) + self.calcsizestring(self.variant) + self.calcsizestring(self.betting_structure)

    def __str__(self):
        return Packet.__str__(self) + "\n\tid = %d, name = %s, variant = %s, betting_structure = %s, seats = %d, average_pot = %d, hands_per_hour = %d, percent_flop = %d, players = %d, observers = %d, waiting = %d, timeout = %d, custom_money = %d " % ( self.id, self.name, self.variant, self.betting_structure, self.seats, self.average_pot, self.hands_per_hour, self.percent_flop, self.players, self.observers, self.waiting, self.timeout, self.custom_money )
    
PacketFactory[PACKET_POKER_TABLE] = PacketPokerTable

########################################

PACKET_POKER_TABLE_LIST = 141
PacketNames[PACKET_POKER_TABLE_LIST] = "POKER_TABLE_LIST"

class PacketPokerTableList(PacketList):
    """\
Semantics: a list of PACKET_POKER_TABLE packets sent as a
response to a PACKET_POKER_SELECT request.

Direction: server  => client

packets: a list of PACKET_POKER_TABLE packets.
"""
    
    type = PACKET_POKER_TABLE_LIST

    format = "!II"
    format_size = calcsize(format)

    def __init__(self, *args, **kwargs):
        self.players = kwargs.get("players", 0)
        self.tables = kwargs.get("tables", 0)
        PacketList.__init__(self, *args, **kwargs)

    def pack(self):
        return PacketList.pack(self) + pack(PacketPokerTableList.format, self.players, self.tables)

    def unpack(self, block):
        block = PacketList.unpack(self, block)
        (self.players, self.tables) = unpack(PacketPokerTableList.format, block[:PacketPokerTableList.format_size])
        return block[PacketPokerTableList.format_size:]

    def calcsize(self):
        return PacketList.calcsize(self) + PacketPokerTableList.format_size

    def __str__(self):
        return PacketList.__str__(self) + "\n\tplayers = %d, tables = %d" % ( self.players, self.tables )

PacketFactory[PACKET_POKER_TABLE_LIST] = PacketPokerTableList

########################################

PACKET_POKER_SIT = 142
PacketNames[PACKET_POKER_SIT] = "POKER_SIT"

class PacketPokerSit(PacketPokerId):
    """\
Semantics: the player "serial" is willing to participate in
the game "game_id".

Direction: server <=> client

Context: this packet must occur after getting a seat for the
game (i.e. a PACKET_POKER_SEAT is honored by the server). A
number of PACKET_POKER_SIT packets are inferred from the
PACKET_POKER_IN_GAME packet.

serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""
    
    type = PACKET_POKER_SIT

PacketFactory[PACKET_POKER_SIT] = PacketPokerSit

########################################

PACKET_POKER_TABLE_DESTROY = 146
PacketNames[PACKET_POKER_TABLE_DESTROY] = "POKER_TABLE_DESTROY"

class PacketPokerTableDestroy(PacketPokerId):
    """destroy"""
    
    type = PACKET_POKER_TABLE_DESTROY

PacketFactory[PACKET_POKER_TABLE_DESTROY] = PacketPokerTableDestroy

########################################

PACKET_POKER_TIMEOUT_WARNING = 152
PacketNames[PACKET_POKER_TIMEOUT_WARNING] = "POKER_TIMEOUT_WARNING"

class PacketPokerTimeoutWarning(PacketPokerId):
    """\
Semantics: the player "serial" is taking too long to play and will
be folded automatically shortly in the game "game_id".

Direction: server  => client

serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

    type = PACKET_POKER_TIMEOUT_WARNING

    timeout = -1
    format = "!I"
    format_size = calcsize(format)
    
    def __init__(self, *args, **kwargs):
        if kwargs.has_key("timeout"):
            self.timeout = kwargs["timeout"]
        PacketPokerId.__init__(self, *args, **kwargs)
        
    def pack(self):
        return PacketPokerId.pack(self) + pack(PacketPokerTimeoutWarning.format, self.timeout)

    def unpack(self, block):
        block = PacketPokerId.unpack(self, block)
        (self.timeout,) = unpack(PacketPokerTimeoutWarning.format, block[:PacketPokerTimeoutWarning.format_size])
        return block[PacketPokerTimeoutWarning.format_size:]

    def calcsize(self):
        return PacketPokerId.calcsize(self) + PacketPokerTimeoutWarning.format_size

    def __str__(self):
        return PacketPokerId.__str__(self) + " timeout = %d" % self.timeout

PacketFactory[PACKET_POKER_TIMEOUT_WARNING] = PacketPokerTimeoutWarning

########################################

PACKET_POKER_TIMEOUT_NOTICE = 153
PacketNames[PACKET_POKER_TIMEOUT_NOTICE] = "POKER_TIMEOUT_NOTICE"

class PacketPokerTimeoutNotice(PacketPokerId):
    """\
Semantics: the player "serial" is took too long to play and has
been folded in the game "game_id".

Direction: server  => client

serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""
    
    type = PACKET_POKER_TIMEOUT_NOTICE

PacketFactory[PACKET_POKER_TIMEOUT_NOTICE] = PacketPokerTimeoutNotice

########################################

PACKET_POKER_SEAT = 154
PacketNames[PACKET_POKER_SEAT] = "POKER_SEAT"

class PacketPokerSeat(PacketPokerId):
    """\
Semantics: the player "serial" is seated on the seat "seat"
in the game "game_id". When a client asks for seat 255,
it instructs the server to chose the first seat available. 
If the server refuses a request, it answers to the
requestor with a PACKET_POKER_SEAT packet with a seat field
set to 255. 

Direction: server <=> client

Context: the player must join the game (PACKET_POKER_TABLE_JOIN)
before issuing a request for a seat. If the request is a success,
the server will send a PACKET_POKER_PLAYER_ARRIVE and a
PACKET_POKER_TABLE_SEATS packet.

seat: a seat number in the interval [0,9] or 255 for an invalid seat.
serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

    type = PACKET_POKER_SEAT

    format = "!B"
    format_size = calcsize(format)
    
    def __init__(self, *args, **kwargs):
        self.seat = kwargs.get("seat", -1)
        PacketPokerId.__init__(self, *args, **kwargs)
        
    def pack(self):
        return PacketPokerId.pack(self) + pack(PacketPokerSeat.format, self.seat)

    def unpack(self, block):
        block = PacketPokerId.unpack(self, block)
        (self.seat,) = unpack(PacketPokerSeat.format, block[:PacketPokerSeat.format_size])
        if self.seat == 255: self.seat = -1
        return block[PacketPokerSeat.format_size:]

    def calcsize(self):
        return PacketPokerId.calcsize(self) + PacketPokerSeat.format_size

    def __str__(self):
        return PacketPokerId.__str__(self) + " seat = %d" % self.seat

PacketFactory[PACKET_POKER_SEAT] = PacketPokerSeat

########################################

PACKET_POKER_TABLE_MOVE = 147
PacketNames[PACKET_POKER_TABLE_MOVE] = "POKER_TABLE_MOVE"

class PacketPokerTableMove(PacketPokerSeat):
    """\
Semantics: move player "serial" from game "game_id" to
game "to_game_id". Special operation meant to reseat a player
from a tournament game to another. The player is automatically
seated at sit-in in the new game.

Direction: server  => client

Context: this packet is equivalent to a PACKET_POKER_LEAVE immediately
followed by a PACKET_POKER_JOIN, a PACKET_POKER_SEAT and a PACKET_POKER_SIT
without the race conditions that would occur if using multiple packets.

serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
to_game_id: integer uniquely identifying a game.
"""

    type = PACKET_POKER_TABLE_MOVE

    format = "!I"
    format_size = calcsize(format)
    
    def __init__(self, *args, **kwargs):
        self.to_game_id = kwargs.get("to_game_id", -1)
        PacketPokerSeat.__init__(self, *args, **kwargs)
        
    def pack(self):
        return PacketPokerSeat.pack(self) + pack(PacketPokerTableMove.format, self.to_game_id)

    def unpack(self, block):
        block = PacketPokerSeat.unpack(self, block)
        (self.to_game_id,) = unpack(PacketPokerTableMove.format, block[:PacketPokerTableMove.format_size])
        return block[PacketPokerTableMove.format_size:]

    def calcsize(self):
        return PacketPokerSeat.calcsize(self) + PacketPokerTableMove.format_size

    def __str__(self):
        return PacketPokerSeat.__str__(self) + " to_game_id = %d" % self.to_game_id

PacketFactory[PACKET_POKER_TABLE_MOVE] = PacketPokerTableMove

########################################

PACKET_POKER_PLAYER_LEAVE = 133
PacketNames[PACKET_POKER_PLAYER_LEAVE] = "POKER_PLAYER_LEAVE"

class PacketPokerPlayerLeave(PacketPokerSeat):
    """\
Semantics: the player "serial" leaves the seat "seat" at game "game_id".

Direction: server <=> client

Context: ineffective in tournament games. If the player is playing a
hand the server will wait until the end of the turn to relay the
packet to other players involved in the same hand. A player is allowed
to leave in the middle of the game but the server hides this to the
other players.

serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
seat: the seat left in the range [0,9]
"""

    TOURNEY = 1
    
    type = PACKET_POKER_PLAYER_LEAVE

PacketFactory[PACKET_POKER_PLAYER_LEAVE] = PacketPokerPlayerLeave

########################################

PACKET_POKER_SIT_OUT = 155
PacketNames[PACKET_POKER_SIT_OUT] = "POKER_SIT_OUT"

class PacketPokerSitOut(PacketPokerId):
    """\
Semantics: the player "serial" seated at the game "game_id"
is now sit out, i.e. not willing to participate in the game.

Direction: server <=> client

Context: if the game is not running (i.e. not between PACKET_POKER_START
packet and a PACKET_POKER_STATE with state == "end" or a PACKET_POKER_CANCELED )
or still in the blind / ante phase (i.e. the last PACKET_POKER_STATE was
state == "blindAnte"), the server honors the request immediately and broadcasts the packet
to all the players watching or participating in the game. If the game
is running and is not in the blind / ante phase, the request is
interpreted as a will to fold (equivalent to PACKET_POKER_FOLD) when
the player comes in position and to sit out when the game ends
(i.e. the PACKET_POKER_SIT_OUT is postponed to the end of the game).

serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""
    
    type = PACKET_POKER_SIT_OUT

PacketFactory[PACKET_POKER_SIT_OUT] = PacketPokerSitOut

########################################

PACKET_POKER_TABLE_QUIT = 156
PacketNames[PACKET_POKER_TABLE_QUIT] = "POKER_TABLE_QUIT"

class PacketPokerTableQuit(PacketPokerId):
    """\
Semantics: the player "serial" is will to be disconnected from
game "game_id".

Direction: server <=  client / client <=> client

Context: inferred when sent to the server because no answer
is expected from the server.

serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

    type = PACKET_POKER_TABLE_QUIT

PacketFactory[PACKET_POKER_TABLE_QUIT] = PacketPokerTableQuit

########################################

PACKET_POKER_BUY_IN = 159
PacketNames[PACKET_POKER_BUY_IN] = "POKER_BUY_IN"

class PacketPokerBuyIn(PacketPokerId):
    """\
Semantics: the player "serial" is willing to participate in
the game "game_id" with an amount equal to "amount". The server
will ensure that the "amount" fits the game constraints (i.e.
player bankroll or betting structure limits).

Direction: server <=  client.

Context: this packet must occur after a successfull PACKET_POKER_SEAT
and before a PACKET_POKER_SIT for the same player. The minimum/maximum
buy in are determined by the betting structure of the game, as
specified in the PACKET_POKER_TABLE packet. 

amount: integer specifying the amount to bring to the game.
serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

    type = PACKET_POKER_BUY_IN

    amount = 0
    format = "!I"
    format_size = calcsize(format)
    
    def __init__(self, *args, **kwargs):
        if kwargs.has_key("amount"):
            self.amount = kwargs["amount"]
        PacketPokerId.__init__(self, *args, **kwargs)
        
    def pack(self):
        return PacketPokerId.pack(self) + pack(PacketPokerBuyIn.format, self.amount)

    def unpack(self, block):
        block = PacketPokerId.unpack(self, block)
        (self.amount,) = unpack(PacketPokerBuyIn.format, block[:PacketPokerBuyIn.format_size])
        return block[PacketPokerBuyIn.format_size:]

    def calcsize(self):
        return PacketPokerId.calcsize(self) + PacketPokerBuyIn.format_size

    def __str__(self):
        return PacketPokerId.__str__(self) + " amount = %d" % self.amount

PacketFactory[PACKET_POKER_BUY_IN] = PacketPokerBuyIn

########################################

PACKET_POKER_REBUY = 164
PacketNames[PACKET_POKER_REBUY] = "POKER_REBUY"

class PacketPokerRebuy(PacketPokerBuyIn):

    type = PACKET_POKER_REBUY

PacketFactory[PACKET_POKER_REBUY] = PacketPokerRebuy

########################################

PACKET_POKER_CHAT = 160
PacketNames[PACKET_POKER_CHAT] = "POKER_CHAT"

class PacketPokerChat(PacketPokerId):

   type = PACKET_POKER_CHAT

   message = 0
   
   def __init__(self, *args, **kwargs):
       if kwargs.has_key("message"):
           self.message = kwargs["message"]
       PacketPokerId.__init__(self, *args, **kwargs)

   def pack(self):
       return PacketPokerId.pack(self) + self.packstring(self.message)
 
   def unpack(self, block):
       block = PacketPokerId.unpack(self, block)
       (block, self.message) = self.unpackstring(block)
       return block
 
   def calcsize(self):
       return PacketPokerId.calcsize(self) + self.calcsizestring(self.message)
 
   def __str__(self):
       return PacketPokerId.__str__(self) + " message = %s" % self.message

PacketFactory[PACKET_POKER_CHAT] = PacketPokerChat

########################################

PACKET_POKER_PLAYER_NO_CARDS = 161
PacketNames[PACKET_POKER_PLAYER_NO_CARDS] = "POKER_PLAYER_NO_CARDS"

class PacketPokerPlayerNoCards(PacketPokerId):
    """\
Semantics: the player "serial" has no cards in game "game_id".

Direction: client <=> client

Context: inferred at showdown.

serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""
    
    type = PACKET_POKER_PLAYER_NO_CARDS

PacketFactory[PACKET_POKER_PLAYER_NO_CARDS] = PacketPokerPlayerNoCards

########################################

PACKET_POKER_PLAYER_INFO = 162
PacketNames[PACKET_POKER_PLAYER_INFO] = "POKER_PLAYER_INFO"

class PacketPokerPlayerInfo(PacketPokerId):
   """\
Semantics: the player "serial" descriptive informations. When
sent to the server, sets the information and broadcast them
to other players. When sent from the server, notify the client
of a change in the player descriptive informations.

Direction: server <=> client 

name: login name of the player.
url: outfit url to load from
outfit: name of the player outfit.
serial: integer uniquely identifying a player.
"""

   NOT_LOGGED = 1
    
   type = PACKET_POKER_PLAYER_INFO

   def __init__(self, *args, **kwargs):
       self.name = kwargs.get('name', "noname")
       self.url = kwargs.get('url', "random")
       self.outfit = kwargs.get('outfit',"random")
       PacketPokerId.__init__(self, *args, **kwargs)

   def pack(self):
       return PacketPokerId.pack(self) + self.packstring(self.name) + self.packstring(self.outfit) + self.packstring(self.url)
 
   def unpack(self, block):
       block = PacketPokerId.unpack(self, block)
       (block, self.name) = self.unpackstring(block)
       (block, self.outfit) = self.unpackstring(block)
       (block, self.url) = self.unpackstring(block)
       return block
 
   def calcsize(self):
       return PacketPokerId.calcsize(self) + self.calcsizestring(self.name) + self.calcsizestring(self.outfit) + self.calcsizestring(self.url)
 
   def __str__(self):
       return PacketPokerId.__str__(self) + " name = %s, url = %s, outfit = %s " % ( self.name , self.url, self.outfit )

PacketFactory[PACKET_POKER_PLAYER_INFO] = PacketPokerPlayerInfo

########################################

PACKET_POKER_PLAYER_ARRIVE = 163
PacketNames[PACKET_POKER_PLAYER_ARRIVE] = "POKER_PLAYER_ARRIVE"

class PacketPokerPlayerArrive(PacketPokerPlayerInfo):
    """\
Semantics: the player "serial" is seated at the game "game_id".
Descriptive information for the player such as "name" and "outfit"
is provided.

Direction: server  => client

Context: this packet is the server answer to successfull
PACKET_POKER_SEAT request. The actual seat allocated to the player
will be specified in the next PACKET_POKER_SEATS packet.

name: login name of the player.
outfit: unique name of the player outfit.
serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

    type = PACKET_POKER_PLAYER_ARRIVE

    format = "!BBBBBBBB"
    format_size = calcsize(format)

    def __init__(self, *args, **kwargs):
        self.blind = kwargs.get("blind", "late")
        self.remove_next_turn = kwargs.get("remove_next_turn", False)
        self.sit_out = kwargs.get("sit_out", True)
        self.sit_out_next_turn = kwargs.get("sit_out_next_turn", False)
        self.auto = kwargs.get("auto", False)
        self.auto_blind_ante = kwargs.get("auto_blind_ante", False)
        self.wait_for = kwargs.get("wait_for", False)
        self.buy_in_payed = kwargs.get("buy_in_payed", False)
        self.seat = kwargs.get("seat", None)
        PacketPokerPlayerInfo.__init__(self, *args, **kwargs)

    def pack(self):
        blind = str(self.blind)
        remove_next_turn = self.remove_next_turn and 1 or 0
        sit_out = self.sit_out and 1 or 0
        sit_out_next_turn = self.sit_out_next_turn and 1 or 0
        auto = self.auto and 1 or 0
        auto_blind_ante = self.auto_blind_ante and 1 or 0
        wait_for = self.wait_for and 1 or 0
        buy_in_payed = self.buy_in_payed and 1 or 0
        seat = self.seat == None and 255 or self.seat
        return PacketPokerPlayerInfo.pack(self) + self.packstring(blind) + pack(PacketPokerPlayerArrive.format, remove_next_turn, sit_out, sit_out_next_turn, auto, auto_blind_ante, wait_for, buy_in_payed, seat)
        
    def unpack(self, block):
        block = PacketPokerPlayerInfo.unpack(self, block)
        (block, blind) = self.unpackstring(block)
        if blind == 'None':
            self.blind = None
        elif blind == 'False':
            self.blind = False
        else:
            self.blind = blind
        ( remove_next_turn, sit_out, sit_out_next_turn, auto, auto_blind_ante, wait_for, buy_in_payed, seat ) = unpack(PacketPokerPlayerArrive.format, block[:PacketPokerPlayerArrive.format_size])
        self.remove_next_turn = remove_next_turn == 1
        self.sit_out = sit_out == 1
        self.sit_out_next_turn = sit_out_next_turn == 1
        self.auto = auto == 1
        self.auto_blind_ante = auto_blind_ante == 1
        self.wait_for = wait_for == 1
        self.buy_in_payed = buy_in_payed == 1
        if seat == 255:
            self.seat = None
        else:
            self.seat = seat
        return block[PacketPokerPlayerArrive.format_size:]

    def calcsize(self):
        return PacketPokerPlayerInfo.calcsize(self) + self.calcsizestring(str(self.blind)) + PacketPokerPlayerArrive.format_size

    def __str__(self):
        return PacketPokerPlayerInfo.__str__(self) + "blind = %s, remove_next_turn = %s, sit_out = %s, sit_out_next_turn = %s, auto = %s, auto_blind_ante = %s, wait_for = %s, buy_in_payed = %s, seat = %s " % ( self.blind, self.remove_next_turn, self.sit_out, self.sit_out_next_turn, self.auto, self.auto_blind_ante, self.wait_for, self.buy_in_payed, self.seat )

PacketFactory[PACKET_POKER_PLAYER_ARRIVE] = PacketPokerPlayerArrive

######################################## 

PACKET_POKER_CHIPS_PLAYER2BET = 165
PacketNames[PACKET_POKER_CHIPS_PLAYER2BET] = "POKER_CHIPS_PLAYER2BET"

class PacketPokerChipsPlayer2Bet(PacketPokerId):
    """\
Semantics: move "chips" from the player "serial" money chip stack
to the bet chip stack.

Direction: client <=> client

chips: list of integers counting the number of chips to move.
     The value of each chip is, respectively:
     1 2 5 10 20 25 50 100 250 500 1000 2000 5000.
serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

    type = PACKET_POKER_CHIPS_PLAYER2BET

    def __init__(self, *args, **kwargs):
        PacketPokerId.__init__(self, *args, **kwargs)
        self.chips = kwargs["chips"]
        
    def __str__(self):
        return PacketPokerId.__str__(self) + " chips = %s" % ( self.chips )

PacketFactory[PACKET_POKER_CHIPS_PLAYER2BET] = PacketPokerChipsPlayer2Bet

######################################## 

PACKET_POKER_CHIPS_BET2POT = 166
PacketNames[PACKET_POKER_CHIPS_BET2POT] = "POKER_CHIPS_BET2POT"

class PacketPokerChipsBet2Pot(PacketPokerId):
    """\
Semantics: move "chips" from the player "serial" bet chip stack
to the "pot" pot.

Direction: client <=> client

Context: the pot index is by definition in the range [0,9] because
it starts at 0 and because there cannot be more pots than players.
The creation of side pots is inferred by the client when a player
is all-in and it is guaranteed that pots are numbered sequentially.

pot: the pot index in the range [0,9].
chips: list of integers counting the number of chips to move.
     The value of each chip is, respectively:
     1 2 5 10 20 25 50 100 250 500 1000 2000 5000.
serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

    type = PACKET_POKER_CHIPS_BET2POT

    def __init__(self, *args, **kwargs):
        PacketPokerId.__init__(self, *args, **kwargs)
        self.chips = kwargs["chips"]
        self.pot = kwargs["pot"]
        
    def __str__(self):
        return PacketPokerId.__str__(self) + " chips = %s, pot = %d" % ( self.chips, self.pot )
    
PacketFactory[PACKET_POKER_CHIPS_BET2POT] = PacketPokerChipsBet2Pot

######################################## Display packet

PACKET_POKER_CHIPS_POT2PLAYER = 167
PacketNames[PACKET_POKER_CHIPS_POT2PLAYER] = "POKER_CHIPS_POT2PLAYER"

class PacketPokerChipsPot2Player(PacketPokerId):
    """\
Semantics: move "chips" from the pot "pot" to the player "serial"
money chip stack. The string "reason" explains why these chips 
are granted to the player. If reason is "win", it means the player
won the chips either because all other players folded or because
he had the best hand at showdown. If reason is "uncalled", it means
the chips are returned to him because no other player was will or
able to call his wager. If reason is "left-over", it means the chips
are granted to him because there was an odd chip while splitting the pot.

Direction: client <=> client

Context: the pot index is by definition in the range [0,9] because
it starts at 0 and because there cannot be more pots than players.
The creation of side pots is inferred by the client when a player
is all-in and it is guaranteed that pots are numbered sequentially.

reason: may be one of "win", "uncalled", "left-over"
pot: the pot index in the range [0,9].
chips: list of integers counting the number of chips to move.
     The value of each chip is, respectively:
     1 2 5 10 20 25 50 100 250 500 1000 2000 5000.
serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

    type = PACKET_POKER_CHIPS_POT2PLAYER

    def __init__(self, *args, **kwargs):
        PacketPokerId.__init__(self, *args, **kwargs)
        self.chips = kwargs.get("chips", [])
        self.pot = kwargs.get("pot", -1)
        self.reason = kwargs.get("reason", "")
        
    def __str__(self):
        return PacketPokerId.__str__(self) + " chips = %s, pot = %d, reason = %s" % ( self.chips, self.pot, self.reason )
    
PacketFactory[PACKET_POKER_CHIPS_POT2PLAYER] = PacketPokerChipsPot2Player

######################################## Display packet

PACKET_POKER_CHIPS_POT_MERGE = 168
PacketNames[PACKET_POKER_CHIPS_POT_MERGE] = "POKER_CHIPS_POT_MERGE"

class PacketPokerChipsPotMerge(PacketPokerId):
    """\
Semantics: merge the pots whose indexes are listed in
"sources" into a single pot at index "destination" in game "game_id".

Direction: client <=> client

Context: when generating PACKET_POKER_CHIPS_POT2PLAYER packets, if
multiple packet can be avoided by merging pots (e.g. when one player
wins all the pots).

destination: a pot index in the range [0,9].
sources: list of pot indexes in the range [0,9].
game_id: integer uniquely identifying a game.
"""

    type = PACKET_POKER_CHIPS_POT_MERGE

    def __init__(self, *args, **kwargs):
        PacketPokerId.__init__(self, *args, **kwargs)
        self.sources = kwargs["sources"]
        self.destination = kwargs["destination"]
        
    def __str__(self):
        return PacketPokerId.__str__(self) + " sources = %s, destination = %d" % ( self.sources, self.destination )

PacketFactory[PACKET_POKER_CHIPS_POT_MERGE] = PacketPokerChipsPotMerge

######################################## Display packet

PACKET_POKER_CHIPS_POT_RESET = 169
PacketNames[PACKET_POKER_CHIPS_POT_RESET] = "POKER_CHIPS_POT_RESET"

class PacketPokerChipsPotReset(PacketPokerId):
    """\
Semantics: all pots for game "game_id" are set to zero.

Direction: client <=> client

Context: it is inferred after a PACKET_POKER_TABLE or a
PACKET_POKER_START packet is sent by the server. It is inferred
after the pot is distributed (i.e. after the game terminates
because a PACKET_POKER_WIN or PACKET_POKER_CANCELED is received).

game_id: integer uniquely identifying a game.
"""
    
    type = PACKET_POKER_CHIPS_POT_RESET

PacketFactory[PACKET_POKER_CHIPS_POT_RESET] = PacketPokerChipsPotReset

######################################## Display packet

PACKET_POKER_END_ROUND = 170
PacketNames[PACKET_POKER_END_ROUND] = "POKER_END_ROUND"

class PacketPokerEndRound(PacketPokerId):
    """\
Semantics: closes a betting round for game "game_id".

Direction: client <=> client

Context: inferred at the end of a sequence of packet related to
a betting round. Paying the blind / ante is not considered a
betting round. This packet is sent when the client side
knows that the round is finished but before the corresponding
packet (PACKET_POKER_STATE) has been received from the server.
It will be followed by the POKER_BEGIN_ROUND packet, either
immediatly if the server has no delay between betting rounds
or later if the server waits a few seconds between two betting
rounds.
It is not inferred at the end of the last betting round.

game_id: integer uniquely identifying a game.
"""
    
    type = PACKET_POKER_END_ROUND

PacketFactory[PACKET_POKER_END_ROUND] = PacketPokerEndRound

########################################

PACKET_POKER_HAND_SELECT = 171
PacketNames[PACKET_POKER_HAND_SELECT] = "POKER_HAND_SELECT"

class PacketPokerHandSelect(PacketString):
    """\
Semantics: query the hand history for player "serial"
and filter them according to the "string" boolean expression.
Return slice of the matching hands that are in the range
["start", "start" + "count"[

Direction: server <=  client

Context: the answer of the server to this query is a
PACKET_POKER_HAND_LIST packet.

string: a valid SQL WHERE expression on the hands table. The
available fields are "name" for the symbolic name of the hand,
"description" for the python expression describing the hand, "serial"
for the unique identifier of the hand also known as the hand_serial
in the PACKET_POKER_START packet.
start: index of the first matching hand
count: number of matching hands to return starting from start
serial: integer uniquely identifying a player.
"""
    
    type = PACKET_POKER_HAND_SELECT

    format = "!IB"
    format_size = calcsize(format)

    def __init__(self, *args, **kwargs):
        self.start = kwargs.get("start", 0)
        self.count = kwargs.get("count", 50)
        PacketString.__init__(self, *args, **kwargs)

    def pack(self):
        return PacketString.pack(self) + pack(PacketPokerHandSelect.format, self.start, self.count)

    def unpack(self, block):
        block = PacketString.unpack(self, block)
        (self.start, self.count) = unpack(PacketPokerHandSelect.format, block[:PacketPokerHandSelect.format_size])
        return block[PacketPokerHandSelect.format_size:]

    def calcsize(self):
        return PacketString.calcsize(self) + PacketPokerHandSelect.format_size

    def __str__(self):
        return PacketString.__str__(self) + " start = %d, count = %d" % ( self.start, self.count )

PacketFactory[PACKET_POKER_HAND_SELECT] = PacketPokerHandSelect

########################################

PACKET_POKER_HAND_LIST = 172
PacketNames[PACKET_POKER_HAND_LIST] = "POKER_HAND_LIST"

class PacketPokerHandList(PacketPokerHandSelect):
    """\
Semantics: a list of hand serials known to the server.

Direction: server  => client

Context: reply to the PACKET_POKER_HAND_SELECT packet.

hands: list of integers uniquely identifying a hand to the server.
"""

    type = PACKET_POKER_HAND_LIST

    format = "!I"
    format_size = calcsize(format)
    format_element = "!I"

    def __init__(self, *args, **kwargs):
        self.hands = kwargs.get("hands", [])
        self.total = kwargs.get("total", -1)
        PacketPokerHandSelect.__init__(self, *args, **kwargs)

    def pack(self):
        block = PacketPokerHandSelect.pack(self)
        block += self.packlist(self.hands, PacketPokerHandList.format_element)
        return block + pack(PacketPokerHandList.format, self.total)

    def unpack(self, block):
        block = PacketPokerHandSelect.unpack(self, block)
        (block, self.hands) = self.unpacklist(block, PacketPokerHandList.format_element)
        (self.total,) = unpack(PacketPokerHandList.format, block[:PacketPokerHandList.format_size])
        return block[PacketPokerHandList.format_size:]

    def calcsize(self):
        return PacketPokerHandSelect.calcsize(self) + self.calcsizelist(self.hands, PacketPokerHandList.format_element) + PacketPokerHandList.format_size

    def __str__(self):
        return PacketPokerHandSelect.__str__(self) + " hands = %s, total = %d" % ( self.hands, self.total )

PacketFactory[PACKET_POKER_HAND_LIST] = PacketPokerHandList

########################################

PACKET_POKER_HAND_REPLAY = 173
PacketNames[PACKET_POKER_HAND_REPLAY] = "POKER_HAND_REPLAY"

class PacketPokerHandReplay(PacketPokerId):
    """"""

    type = PACKET_POKER_HAND_REPLAY

PacketFactory[PACKET_POKER_HAND_REPLAY] = PacketPokerHandReplay

########################################

PACKET_POKER_HAND_SELECT_ALL = 174
PacketNames[PACKET_POKER_HAND_SELECT_ALL] = "POKER_HAND_SELECT_ALL"

class PacketPokerHandSelectAll(PacketString):
    """
Semantics: query the hand history for all players
and filter them according to the "string" boolean expression.
The user must be logged in and have administrative permissions
for this query to succeed.

Direction: server <=  client

Context: the answer of the server to this query is a
PACKET_POKER_HAND_LIST packet. 

string: a valid SQL WHERE expression on the hands table. The
available fields are "name" for the symbolic name of the hand,
"description" for the python expression describing the hand, "serial"
for the unique identifier of the hand also known as the hand_serial
in the PACKET_POKER_START packet.
"""
    
    type = PACKET_POKER_HAND_SELECT_ALL

PacketFactory[PACKET_POKER_HAND_SELECT_ALL] = PacketPokerHandSelectAll

######################################## Display packet

PACKET_POKER_CHIPS_BET2PLAYER = 175
PacketNames[PACKET_POKER_CHIPS_BET2PLAYER] = "POKER_CHIPS_BET2PLAYER"

class PacketPokerChipsBet2player(PacketPokerChipsPlayer2Bet):
    """chips move from bet to player"""

    type = PACKET_POKER_CHIPS_BET2PLAYER

PacketFactory[PACKET_POKER_CHIPS_BET2PLAYER] = PacketPokerChipsBet2player

########################################

PACKET_POKER_USER_INFO = 176
PacketNames[PACKET_POKER_USER_INFO] = "POKER_USER_INFO"

class PacketPokerUserInfo(PacketSerial):
    """\
Semantics: read only user descritpive information, complement
of PACKET_POKER_PLAYER_INFO.

Direction: server  => client

Context: answer to the PACKET_POKER_GET_USER_INFO packet.

play_money: total amount of play money.
custom_money: total amount of custom money.
point_money: total amount of point money.
rating: server wide ELO rating.
serial: integer uniquely identifying a player.
"""

    NOT_LOGGED = 1
    
    type = PACKET_POKER_USER_INFO
    play_money = -1
    play_money_in_game = -1
    custom_money = -1
    custom_money_in_game = -1
    point_money = -1
    rating = 1500
    
    format = "!IIIIII"
    format_size = calcsize(format)

    def __init__(self, *args, **kwargs):
        self.play_money = kwargs.get("play_money", -1)
        self.play_money_in_game = kwargs.get("play_money_in_game", -1)
        self.custom_money = kwargs.get("custom_money", -1)
        self.custom_money_in_game = kwargs.get("custom_money_in_game", -1)
        self.point_money = kwargs.get("point_money", -1)
        self.rating = kwargs.get("rating", 1500)
        PacketSerial.__init__(self, *args, **kwargs)

    def pack(self):
        return PacketSerial.pack(self) + pack(PacketPokerUserInfo.format, self.play_money, self.play_money_in_game, self.custom_money, self.custom_money_in_game, self.point_money, self.rating)
        
    def unpack(self, block):
        block = PacketSerial.unpack(self, block)
        (self.play_money, self.play_money_in_game, self.custom_money, self.custom_money_in_game, self.point_money, self.rating) = unpack(PacketPokerUserInfo.format, block[:PacketPokerUserInfo.format_size])
        return block[PacketPokerUserInfo.format_size:]

    def calcsize(self):
        return PacketSerial.calcsize(self) + PacketPokerUserInfo.format_size

    def __str__(self):
        return PacketSerial.__str__(self) + " play_money = %d, play_money_in_game = %d, custom_money = %d, custom_money_in_game = %d, point_money = %d, rating = %d" % ( self.play_money, self.play_money_in_game, self.custom_money,  self.custom_money_in_game, self.point_money, self.rating )

PacketFactory[PACKET_POKER_USER_INFO] = PacketPokerUserInfo

########################################

PACKET_POKER_GET_USER_INFO = 177
PacketNames[PACKET_POKER_GET_USER_INFO] = "POKER_GET_USER_INFO"

class PacketPokerGetUserInfo(PacketSerial):
    """\
Semantics: request the read only descriptive information
for player "serial".

Direction: server <=  client

Context: a user must first login (PACKET_LOGIN) successfully
before sending this packet. 

serial: integer uniquely identifying a player.
"""
    
    type = PACKET_POKER_GET_USER_INFO

PacketFactory[PACKET_POKER_GET_USER_INFO] = PacketPokerGetUserInfo

########################################

PACKET_POKER_INT = 178
PacketNames[PACKET_POKER_INT] = "POKER_INT"

class PacketPokerInt(PacketPokerId):
    """base class for a int coded amount"""

    type = PACKET_POKER_INT

    amount = 0
    format = "!I"
    format_size = calcsize(format)
    
    def __init__(self, *args, **kwargs):
        if kwargs.has_key("amount"):
            self.amount = kwargs["amount"]
        PacketPokerId.__init__(self, *args, **kwargs)
        
    def pack(self):
        return PacketPokerId.pack(self) + pack(PacketPokerInt.format, self.amount)

    def unpack(self, block):
        block = PacketPokerId.unpack(self, block)
        (self.amount,) = unpack(PacketPokerInt.format, block[:PacketPokerInt.format_size])
        return block[PacketPokerInt.format_size:]

    def calcsize(self):
        return PacketPokerId.calcsize(self) + PacketPokerInt.format_size

    def __str__(self):
        return PacketPokerId.__str__(self) + " amount = %d" % self.amount

PacketFactory[PACKET_POKER_INT] = PacketPokerInt

########################################

PACKET_POKER_ANTE = 179
PacketNames[PACKET_POKER_ANTE] = "POKER_ANTE"

class PacketPokerAnte(PacketPokerInt):
    """\
Semantics: the player "serial" paid an amount of
"amount" for the ante in game "game_id".

Direction: server <=> client

Context: the server always sends a PACKET_POKER_POSITION before
sending this packet. The client may send this packet after
receiving a PACKET_POKER_ANTE_REQUEST.

Note: the amount may be lower than requested by the betting structure
when in tournament. Ring games will refuse a player to enter the with
less than the required amount for blind or/and antes.

amount: amount paid for the ante.
serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""
    
    type = PACKET_POKER_ANTE

PacketFactory[PACKET_POKER_ANTE] = PacketPokerAnte

########################################

PACKET_POKER_BLIND = 180
PacketNames[PACKET_POKER_BLIND] = "POKER_BLIND"

class PacketPokerBlind(PacketPokerInt):
    """\
Semantics: the player "serial" paid an amount of
"amount" for the blind and "dead" for the dead
in game "game_id".

Direction: server <=> client

Context: the server always sends a PACKET_POKER_POSITION before
sending this packet. The client may send this packet after
receiving a PACKET_POKER_BLIND_REQUEST.

Note: the dead and amount fields are ignored in packets sent
to the server. They are calculated by the server according to
the state of the game.

Note: the amount may be lower than requested by the betting structure
when in tournament. Ring games will refuse a player to enter the with
less than the required amount for blind or/and antes.

dead: amount paid for the dead (goes to the pot).
amount: amount paid for the blind (live for the next betting round).
serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

    type = PACKET_POKER_BLIND

    dead = 0
    format = "!I"
    format_size = calcsize(format)
    
    def __init__(self, *args, **kwargs):
        self.dead = kwargs.get("dead", 0)
        PacketPokerInt.__init__(self, *args, **kwargs)
        
    def pack(self):
        return PacketPokerInt.pack(self) + pack(PacketPokerBlind.format, self.dead)

    def unpack(self, block):
        block = PacketPokerInt.unpack(self, block)
        (self.dead,) = unpack(PacketPokerBlind.format, block[:PacketPokerBlind.format_size])
        return block[PacketPokerBlind.format_size:]

    def calcsize(self):
        return PacketPokerInt.calcsize(self) + PacketPokerBlind.format_size

    def __str__(self):
        return PacketPokerInt.__str__(self) + " dead = %d" % self.dead

PacketFactory[PACKET_POKER_BLIND] = PacketPokerBlind

########################################

PACKET_POKER_WAIT_BIG_BLIND = 181
PacketNames[PACKET_POKER_WAIT_BIG_BLIND] = "POKER_WAIT_BIG_BLIND"

class PacketPokerWaitBigBlind(PacketPokerId):
    """\
Semantics: the player "serial" wants to wait for the big blind
to reach his seat in game "game_id" before entering the game.

Direction: server <=  client

Context: answer to a PACKET_POKER_BLIND_REQUEST. The server
will implicitly sit out the player by not including him in
the PACKET_POKER_IN_GAME packet sent at the end of the "blindAnte"
round. The PACKET_POKER_WAIT_FOR packet is inferred to avoid complex
interpretation of PACKET_POKER_IN_GAME and can be considered
equivalent to a PACKET_POKER_SIT_OUT packet if the distinction is
not important to the client.

serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""
    
    type = PACKET_POKER_WAIT_BIG_BLIND

PacketFactory[PACKET_POKER_WAIT_BIG_BLIND] = PacketPokerWaitBigBlind

########################################

PACKET_POKER_AUTO_BLIND_ANTE = 183
PacketNames[PACKET_POKER_AUTO_BLIND_ANTE] = "POKER_AUTO_BLIND_ANTE"

class PacketPokerAutoBlindAnte(PacketPokerId):
    """\
Semantics: the player "serial" asks the server to automatically
post the blinds or/and antes for game "game_id".

Direction: server <=  client

Context: by default the server will not automatically post
the blinds or/and antes.

serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""
    
    type = PACKET_POKER_AUTO_BLIND_ANTE

PacketFactory[PACKET_POKER_AUTO_BLIND_ANTE] = PacketPokerAutoBlindAnte

########################################

PACKET_POKER_NOAUTO_BLIND_ANTE = 184
PacketNames[PACKET_POKER_NOAUTO_BLIND_ANTE] = "POKER_NOAUTO_BLIND_ANTE"

class PacketPokerNoautoBlindAnte(PacketPokerId):
    """\
Semantics: the player "serial" asks the server to send
a PACKET_POKER_BLIND_REQUEST or/and PACKET_POKER_ANTE_REQUEST
when a blind or/and ante for game "game_id" must be paid.

Direction: server <=  client

Context: by default the server behaves in this way.

serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""
    
    type = PACKET_POKER_NOAUTO_BLIND_ANTE

PacketFactory[PACKET_POKER_NOAUTO_BLIND_ANTE] = PacketPokerNoautoBlindAnte

########################################

PACKET_POKER_CANCELED = 185
PacketNames[PACKET_POKER_CANCELED] = "POKER_CANCELED"

class PacketPokerCanceled(PacketPokerInt):
    """\
Semantics: the game is canceled because only the player
"serial" is willing to pay the blinds or/and antes.
The "amount" paid by the player is returned to him. If
no player is willing to pay the blinds or/and antes, the
serial is zero.

Direction: server  => client

amount: the amount to return to the player.
serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""
    
    type = PACKET_POKER_CANCELED

PacketFactory[PACKET_POKER_CANCELED] = PacketPokerCanceled

########################################

PACKET_POKER_DISPLAY_NODE = 186
PacketNames[PACKET_POKER_DISPLAY_NODE] = "POKER_DISPLAY_NODE"

class PacketPokerDisplayNode(Packet):
    """request POKER_DISPLAY_NODE packet"""
    
    type = PACKET_POKER_DISPLAY_NODE

    def __init__(self, *args, **kwargs):
        self.name = kwargs.get("name", "")
        self.state = kwargs.get("state", "")
        self.style = kwargs.get("style", "")
        self.selection = kwargs.get("selection", None)

    def __str__(self):
        return Packet.__str__(self) + " name = %s, state = %s, style = %s, selection = %s " % ( self.name, self.state, self.style, self.selection )

PacketFactory[PACKET_POKER_DISPLAY_NODE] = PacketPokerDisplayNode

######################################## Display packet

PACKET_POKER_DEAL_CARDS = 187
PacketNames[PACKET_POKER_DEAL_CARDS] = "POKER_DEAL_CARDS"

class PacketPokerDealCards(PacketPokerId):
    """\
Semantics: deal "numberOfCards" down cards for each player listed
in "serials" in game "game_id".

Direction: client <=> client

Context: inferred after the beginning of a betting round (i.e.
after the PACKET_POKER_STATE packet is received) and after
the chips involved in the previous betting round have been
sorted (i.e. after PACKET_POKER_CHIPS_BET2POT packets are
inferred). Contrary to the PACKET_POKER_PLAYER_CARDS,
this packet is only sent if cards must be dealt. It
is guaranteed that this packet will always occur before
the PACKET_POKER_PLAYER_CARDS that specify the cards to
be dealt and that these packets will follow immediately
after it (no other packet will be inserted between this packet
and the first PACKET_POKER_PLAYER_CARDS). It is also guaranteed
that exactly one PACKET_POKER_PLAYER_CARDS will occur for each
serial listed in "serials".

numberOfCards: number of cards to be dealt.
serials: integers uniquely identifying players.
game_id: integer uniquely identifying a game.
"""

    type = PACKET_POKER_DEAL_CARDS
    numberOfCards = 0
    serials = []

    def __init__(self, *args, **kwargs):
        if kwargs.has_key("numberOfCards"):
            self.numberOfCards = kwargs["numberOfCards"] or 2
        if kwargs.has_key("serials"):
            self.serials = kwargs["serials"] or []
        PacketPokerId.__init__(self, *args, **kwargs)

    def __str__(self):
        return PacketPokerId.__str__(self) + " number of cards = %d, serials = %s" % ( self.numberOfCards, self.serials )

PacketFactory[PACKET_POKER_DEAL_CARDS] = PacketPokerDealCards

########################################

PACKET_POKER_BLIND_REQUEST = 188
PacketNames[PACKET_POKER_BLIND_REQUEST] = "POKER_BLIND_REQUEST"

class PacketPokerBlindRequest(PacketPokerBlind):
    """\
Semantics: the player "serial" is required to pay the a blind
of "amount" and a dead of "dead" for game "game_id". The logical
state of the blind is given in "state".

Direction: server  => client

Context: a PACKET_POKER_POSITION packet is sent by the server before
this packet. The answer may be a PACKET_POKER_SIT_OUT (to refuse to
pay the blind), PACKET_POKER_BLIND (to pay the blind),
PACKET_POKER_WAIT_BIG_BLIND (if not willing to pay a late blind but
willing to pay the big blind when due).

state: "small", "big", "late", "big_and_dead".
dead: amount to pay for the dead (goes to the pot).
amount: amount to pay for the blind (live for the next betting round).
serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

    type = PACKET_POKER_BLIND_REQUEST

    state = "unknown"

    def __init__(self, *args, **kwargs):
        self.state = kwargs.get("state", "unknown")
        PacketPokerBlind.__init__(self, *args, **kwargs)

    def pack(self):
        return PacketPokerBlind.pack(self) + self.packstring(self.state)

    def unpack(self, block):
        block = PacketPokerBlind.unpack(self, block)
        (block, self.state) = self.unpackstring(block)
        return block

    def calcsize(self):
        return PacketPokerBlind.calcsize(self) + self.calcsizestring(self.state)

    def __str__(self):
        return PacketPokerBlind.__str__(self) + " state = %s" % self.state
    
PacketFactory[PACKET_POKER_BLIND_REQUEST] = PacketPokerBlindRequest

########################################

PACKET_POKER_ANTE_REQUEST = 189
PacketNames[PACKET_POKER_ANTE_REQUEST] = "POKER_ANTE_REQUEST"

class PacketPokerAnteRequest(PacketPokerAnte):
    """\
Semantics: the player "serial" is required to pay the an ante
of "amount" for game"game_id".

Direction: server  => client

Context: a PACKET_POKER_POSITION packet is sent by the server before
this packet. The answer may be a PACKET_POKER_SIT_OUT (to refuse to
pay the ante), PACKET_POKER_ANTE (to pay the ante).

amount: amount to pay for the ante.
serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

    type = PACKET_POKER_ANTE_REQUEST

PacketFactory[PACKET_POKER_ANTE_REQUEST] = PacketPokerAnteRequest

########################################

PACKET_POKER_AUTO_FOLD = 190
PacketNames[PACKET_POKER_AUTO_FOLD] = "POKER_AUTO_FOLD"

class PacketPokerAutoFold(PacketPokerId):
    """\
Semantics: the player "serial" will be folded by the server
when in position for tournament game "game_id".

Direction: server  => client

Context: this packet informs the players at the table about
a change of state for a player in tournament games. This
state can be canceled by a PACKET_POKER_SIT packet for the same
player.

serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

    type = PACKET_POKER_AUTO_FOLD

PacketFactory[PACKET_POKER_AUTO_FOLD] = PacketPokerAutoFold

########################################

PACKET_POKER_WAIT_FOR = 191
PacketNames[PACKET_POKER_WAIT_FOR] = "POKER_WAIT_FOR"

class PacketPokerWaitFor(PacketPokerId):
    """\
Semantics: the player "serial" waits for the late
blind (if "reason" == "late") or the big blind (if
"reason" == "big") in game "game_id". Otherwise equivalent
to PACKET_POKER_SIT_OUT.

Direction: server  => client / client <=> client

Context: when sent by the server, it means that the answer of a client
to a PACKET_POKER_BLIND_REQUEST or a PACKET_POKER_ANTE_REQUEST was to
wait for something (i.e.  PACKET_POKER_WAIT_BIG_BLIND) or that the
server denied him the right to play this hand because he was on the
small blind or on the button. When inferred, this packet can be
handled as if it was a PACKET_POKER_SIT_OUT.

reason: either "big" or "late".
serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

    type = PACKET_POKER_WAIT_FOR
    reason = ""

    def __init__(self, *args, **kwargs):
        if kwargs.has_key("reason"):
            self.reason = kwargs["reason"]
        PacketPokerId.__init__(self, *args, **kwargs)
        
    def pack(self):
        return PacketPokerId.pack(self) + self.packstring(self.reason)

    def unpack(self, block):
        block = PacketPokerId.unpack(self, block)
        (block, self.reason) = self.unpackstring(block)
        return block
    
    def calcsize(self):
        return PacketPokerId.calcsize(self) + self.calcsizestring(self.reason)

    def __str__(self):
        return PacketPokerId.__str__(self) + " reason = %s" % self.reason

PacketFactory[PACKET_POKER_WAIT_FOR] = PacketPokerWaitFor

########################################

PACKET_POKER_CHAT_HISTORY = 192
PacketNames[PACKET_POKER_CHAT_HISTORY] = "POKER_CHAT_HISTORY"

class PacketPokerChatHistory(Packet):
    """chat history show"""

    type = PACKET_POKER_CHAT_HISTORY

    def __init__(self, *args, **kwargs):
        self.show = kwargs.get("show", "no")

PacketFactory[PACKET_POKER_CHAT_HISTORY] = PacketPokerChatHistory


########################################

PACKET_POKER_DISPLAY_CARD = 193
PacketNames[PACKET_POKER_DISPLAY_CARD] = "POKER_DISPLAY_CARD"

class PacketPokerDisplayCard(PacketPokerId):
    """Hide a player card"""

    type = PACKET_POKER_DISPLAY_CARD
    index = []
    display = 0

    def __init__(self, *args, **kwargs):
        PacketPokerId.__init__(self, *args, **kwargs)
        self.index = kwargs.get("index", [] )
        self.display = kwargs.get("display", 0 )

PacketFactory[PACKET_POKER_DISPLAY_CARD] = PacketPokerDisplayCard

########################################

PACKET_POKER_SELF_IN_POSITION = 194
PacketNames[PACKET_POKER_SELF_IN_POSITION] = "POKER_SELF_IN_POSITION"

class PacketPokerSelfInPosition(PacketPokerPosition):
    """\
Semantics: the player authenticated for this connection
is in position. Otherwise identical to PACKET_POKER_POSITION.

"""

    type = PACKET_POKER_SELF_IN_POSITION

PacketFactory[PACKET_POKER_SELF_IN_POSITION] = PacketPokerSelfInPosition

########################################

PACKET_POKER_SELF_LOST_POSITION = 195
PacketNames[PACKET_POKER_SELF_LOST_POSITION] = "POKER_SELF_LOST_POSITION"

class PacketPokerSelfLostPosition(PacketPokerPosition):
    """\
Semantics: the player authenticated for this connection
is in position. Otherwise identical to PACKET_POKER_POSITION.

"""

    type = PACKET_POKER_SELF_LOST_POSITION

PacketFactory[PACKET_POKER_SELF_LOST_POSITION] = PacketPokerSelfLostPosition

########################################

PACKET_POKER_HIGHEST_BET_INCREASE = 196
PacketNames[PACKET_POKER_HIGHEST_BET_INCREASE] = "POKER_HIGHEST_BET_INCREASE"

class PacketPokerHighestBetIncrease(PacketPokerId):
    """\
Semantics: a wager was made in game "game_id" that increases
the highest bet amount. 

Direction: client <=> client

Context: inferred whenever a wager is made that changes
the highest bet (live blinds are considered a wager, antes are not).
Inferred once per blindAnte round: when the
first big blind is posted. It is therefore guaranteed not to be posted
if a game is canceled because noone wanted to pay the big blind, even
if someone already posted the small blind. In all other betting rounds it
is inferred for each raise.

game_id: integer uniquely identifying a game.
"""
    
    type = PACKET_POKER_HIGHEST_BET_INCREASE

PacketFactory[PACKET_POKER_HIGHEST_BET_INCREASE] = PacketPokerHighestBetIncrease

########################################

PACKET_POKER_STREAM_MODE = 197
PacketNames[PACKET_POKER_STREAM_MODE] = "POKER_STREAM_MODE"

class PacketPokerStreamMode(PacketPokerId):
    """
Semantics: the packets received after this one are
a stream describing poker games changing as time passes.

Direction: server  => client

Context: this is the default mode in which the packets
are to be interpreted by the client. This packet is
only needed after a PACKET_POKER_BATCH_MODE packet was sent,
to come back to the default mode.

serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

    type = PACKET_POKER_STREAM_MODE

PacketFactory[PACKET_POKER_STREAM_MODE] = PacketPokerStreamMode

########################################

PACKET_POKER_BATCH_MODE = 198
PacketNames[PACKET_POKER_BATCH_MODE] = "POKER_BATCH_MODE"

class PacketPokerBatchMode(PacketPokerId):
    """
Semantics: the packets received after this one are
a batch describing a poker game state at a given point
in time.

Direction: server  => client / client <=> client

Context: the server will send this packet before sending
a batch of packets describing the current state of a game,
such as when joining a table. That may involve a long set
of packets describing the whole action of the game until
showdown. The client is free to replay it (in accelerated
mode or as a play back) or to merely use these packets to
rebuild the state of the game. It is produced by the client
when the resendPacket method is called in order to send a
sequence of packets describing a game for which the client
already knows everything (this is handy when switching tables,
for instance).

serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

    type = PACKET_POKER_BATCH_MODE

PacketFactory[PACKET_POKER_BATCH_MODE] = PacketPokerBatchMode

########################################

PACKET_POKER_LOOK_CARDS = 199
PacketNames[PACKET_POKER_LOOK_CARDS] = "POKER_LOOK_CARDS"

class PacketPokerLookCards(PacketPokerId):
    """\
Semantics: the player "serial" is looking at his cards
in game "game_id".

Direction: server <=> client

serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

    state = "on"

    def __init__(self, *args, **kwargs):
        if kwargs.has_key("state"):
            self.state = kwargs["state"]
        PacketPokerId.__init__(self, *args, **kwargs)

    type = PACKET_POKER_LOOK_CARDS

PacketFactory[PACKET_POKER_LOOK_CARDS] = PacketPokerLookCards


########################################

PACKET_POKER_PLAYER_WIN = 200
PacketNames[PACKET_POKER_PLAYER_WIN] = "POKER_PLAYER_WIN"

class PacketPokerPlayerWin(PacketPokerId):
    """\
Semantics: the player "serial" win.

Direction: client <=> client

Context: when a PacketPokerWin arrive from server. The packet is generated
from PACKET_PLAYER_WIN. For each player that wins something a packet
PlayerWin is generated.

serial: integer uniquely identifying a player.
"""
    type = PACKET_POKER_PLAYER_WIN

PacketFactory[PACKET_POKER_PLAYER_WIN] = PacketPokerPlayerWin

########################################
PACKET_POKER_ANIMATION_PLAYER_NOISE = 201
PacketNames[PACKET_POKER_ANIMATION_PLAYER_NOISE] = "POKER_ANIMATION_PLAYER_NOISE"

class PacketPokerAnimationPlayerNoise(PacketPokerId):
    """\
Semantics: the player "serial" play or stop noise animation.

Direction: client <=> client

Context: a PacketPokerPlayerNoise is send to the client c++ to stop or start
player's noise animation.

serial: integer uniquely identifying a player.
action: string that contain "start" or "stop".
"""
    type = PACKET_POKER_ANIMATION_PLAYER_NOISE

    def __init__(self, *args, **kwargs):
        if kwargs.has_key("action"):
            self.action = kwargs["action"]
        PacketPokerId.__init__(self, *args, **kwargs)

    def __str__(self):
        return Packet.__str__(self) + " serial = %d, action = %s" % ( self.serial, self.action )
    
PacketFactory[PACKET_POKER_ANIMATION_PLAYER_NOISE] = PacketPokerAnimationPlayerNoise

########################################

PACKET_POKER_ANIMATION_PLAYER_FOLD = 202
PacketNames[PACKET_POKER_ANIMATION_PLAYER_FOLD] = "POKER_ANIMATION_PLAYER_FOLD"

class PacketPokerAnimationPlayerFold(PacketPokerId):
    """\
Semantics: the player "serial" play an animation fold.

Direction: client <=> client

Context: a PacketPokerPlayerNoise is send to the client c++ to stop or start
player's noise animation.

serial: integer uniquely identifying a player.
animation: string used to select an animation fold.
"""
    type = PACKET_POKER_ANIMATION_PLAYER_FOLD

    def __init__(self, *args, **kwargs):
        if kwargs.has_key("animation"):
            self.animation = kwargs["animation"]
        PacketPokerId.__init__(self, *args, **kwargs)

    def __str__(self):
        return PacketPokerId.__str__(self) + " serial = %d, animation fold = %s" % ( self.serial, self.animation )
    
PacketFactory[PACKET_POKER_ANIMATION_PLAYER_FOLD] = PacketPokerAnimationPlayerFold

########################################

PACKET_POKER_TABLE_REQUEST_PLAYERS_LIST = 203
PacketNames[PACKET_POKER_TABLE_REQUEST_PLAYERS_LIST] = "POKER_TABLE_REQUEST_PLAYERS_LIST"

class PacketPokerTableRequestPlayersList(PacketPokerId):
    """\
Semantics: client request the player list of the game "game_id".

Direction: client => server

game_id: integer uniquely identifying a game.
"""

    type = PACKET_POKER_TABLE_REQUEST_PLAYERS_LIST

PacketFactory[PACKET_POKER_TABLE_REQUEST_PLAYERS_LIST] = PacketPokerTableRequestPlayersList

########################################

PACKET_POKER_PLAYERS_LIST = 204
PacketNames[PACKET_POKER_PLAYERS_LIST] = "POKER_PLAYERS_LIST"

class PacketPokerPlayersList(PacketPokerId):
    """

    """

    players = []
    format = "!H"
    format_size = calcsize(format)
    format_item = "!IB"
    format_item_size = calcsize(format_item)
    
    type = PACKET_POKER_PLAYERS_LIST

    def __init__(self, *args, **kwargs):
        PacketPokerId.__init__(self, *args, **kwargs)
        self.players = kwargs.get("players", [])

    def pack(self):
        block = PacketPokerId.pack(self) + pack(PacketPokerPlayersList.format, len(self.players))
        for (name, chips, flag) in self.players:
            block += self.packstring(name) + pack(PacketPokerPlayersList.format_item, chips, flag)
        return block

    def unpack(self, block):
        block = PacketPokerId.unpack(self, block)
        (len,) = unpack(PacketPokerPlayersList.format, block[:PacketPokerPlayersList.format_size])
        block = block[PacketPokerPlayersList.format_size:]
        self.players = []
        for i in xrange(len):
            (block, name) = self.unpackstring(block)
            (chips, flag) = unpack(PacketPokerPlayersList.format_item, block[:PacketPokerPlayersList.format_item_size])
            block = block[PacketPokerPlayersList.format_item_size:]
            self.players.append((name, chips, flag))
        return block
        
    def calcsize(self):
        size = PacketPokerId.calcsize(self) + PacketPokerPlayersList.format_size
        for (name, chips, flag) in self.players:
            size += self.calcsizestring(name) + PacketPokerPlayersList.format_item_size
        return size

    def __str__(self):
        string = PacketPokerId.__str__(self) + " player|chips|flag : "
        for (name, chips, flag) in self.players:
            string += " %s|%d|%d " % ( name, chips, flag )
        return string

PacketFactory[PACKET_POKER_PLAYERS_LIST] = PacketPokerPlayersList

########################################

PACKET_POKER_PERSONAL_INFO = 206
PacketNames[PACKET_POKER_PERSONAL_INFO] = "POKER_PERSONAL_INFO"

class PacketPokerPersonalInfo(PacketPokerUserInfo):
    """\
"""

    NOT_LOGGED = 1
    
    type = PACKET_POKER_PERSONAL_INFO

    def __init__(self, *args, **kwargs):
        self.email = kwargs.get("email", "")
        self.addr_street = kwargs.get("addr_street", "")
        self.addr_zip = kwargs.get("addr_zip", "")
        self.addr_town = kwargs.get("addr_town", "")
        self.addr_state = kwargs.get("addr_state", "")
        self.addr_country = kwargs.get("addr_country", "")
        self.phone = kwargs.get("phone", "")
        PacketPokerUserInfo.__init__(self, *args, **kwargs)

    def pack(self):
        packet = PacketPokerUserInfo.pack(self)
        packet += self.packstring(self.email)
        packet += self.packstring(self.addr_street)
        packet += self.packstring(self.addr_zip)
        packet += self.packstring(self.addr_town)
        packet += self.packstring(self.addr_state)
        packet += self.packstring(self.addr_country)
        packet += self.packstring(self.phone)
        return packet
        
    def unpack(self, block):
        block = PacketPokerUserInfo.unpack(self, block)
        (block, self.email) = self.unpackstring(block)
        (block, self.addr_street) = self.unpackstring(block)
        (block, self.addr_zip) = self.unpackstring(block)
        (block, self.addr_town) = self.unpackstring(block)
        (block, self.addr_state) = self.unpackstring(block)
        (block, self.addr_country) = self.unpackstring(block)
        (block, self.phone) = self.unpackstring(block)
        return block

    def calcsize(self):
        return ( PacketPokerUserInfo.calcsize(self) +
                 self.calcsizestring(self.email) +
                 self.calcsizestring(self.addr_street) +
                 self.calcsizestring(self.addr_zip) +
                 self.calcsizestring(self.addr_town) +
                 self.calcsizestring(self.addr_state) +
                 self.calcsizestring(self.addr_country) +
                 self.calcsizestring(self.phone) )

    def __str__(self):
        return PacketPokerUserInfo.__str__(self) + " email = %s, addr_street = %s, addr_zip = %s, addr_town = %s, addr_state = %s, addr_country = %s, phone = %s" % ( self.email, self.addr_street, self.addr_zip, self.addr_town, self.addr_state, self.addr_country, self.phone )

PacketFactory[PACKET_POKER_PERSONAL_INFO] = PacketPokerPersonalInfo

########################################

PACKET_POKER_GET_PERSONAL_INFO = 207
PacketNames[PACKET_POKER_GET_PERSONAL_INFO] = "POKER_GET_PERSONAL_INFO"

class PacketPokerGetPersonalInfo(PacketSerial):
    """\
Semantics: request the read only descriptive information
for player "serial".

Direction: server <=  client

Context: a personal must first login (PACKET_LOGIN) successfully
before sending this packet. 

serial: integer uniquely identifying a player.
"""
    
    NOT_LOGGED = 1
    
    type = PACKET_POKER_GET_PERSONAL_INFO

PacketFactory[PACKET_POKER_GET_PERSONAL_INFO] = PacketPokerGetPersonalInfo

########################################

PACKET_POKER_ANIMATION_PLAYER_BET = 208
PacketNames[PACKET_POKER_ANIMATION_PLAYER_BET] = "POKER_PLAYER_ANIMATION_BET"

class PacketPokerAnimationPlayerBet(PacketPokerId):
    """\
"""
    type = PACKET_POKER_ANIMATION_PLAYER_BET

    def __init__(self, *args, **kwargs):
        if kwargs.has_key("animation"):
            self.animation = kwargs["animation"]
        if kwargs.has_key("chips"):
            self.chips = kwargs["chips"]
        PacketPokerId.__init__(self, *args, **kwargs)

    def __str__(self):
        return PacketPokerId.__str__(self) + " serial = %d, chips %s , animation %s" % ( self.serial ,self.animation, self.chips )
    
PacketFactory[PACKET_POKER_ANIMATION_PLAYER_BET] = PacketPokerAnimationPlayerBet

########################################

PACKET_POKER_ANIMATION_PLAYER_CHIPS = 209
PacketNames[PACKET_POKER_ANIMATION_PLAYER_CHIPS] = "POKER_PLAYER_ANIMATION_CHIPS"

class PacketPokerAnimationPlayerChips(PacketPokerId):
    """\
"""
    type = PACKET_POKER_ANIMATION_PLAYER_CHIPS

    def __init__(self, *args, **kwargs):
        if kwargs.has_key("animation"):
            self.animation = kwargs["animation"]
        if kwargs.has_key("chips"):
            self.chips = kwargs["chips"]
        if kwargs.has_key("state"):
            self.state = kwargs["state"]
        
        PacketPokerId.__init__(self, *args, **kwargs)

    def __str__(self):
        return PacketPokerId.__str__(self) + " serial = %d, chips %s , animation %s" % ( self.serial ,self.animation, self.chips )
    
PacketFactory[PACKET_POKER_ANIMATION_PLAYER_CHIPS] = PacketPokerAnimationPlayerChips

########################################
PACKET_POKER_TOURNEY_SELECT = 210
PacketNames[PACKET_POKER_TOURNEY_SELECT] = "POKER_TOURNEY_SELECT"

class PacketPokerTourneySelect(PacketString):
    """\
Semantics: request the list of tourneys matching the "string" constraint.
The answer is a possibly empty PACKET_POKER_TOURNEY_LIST packet.

Direction: server <=  client

string: a valid SQL WHERE expression. 
"""
    
    type = PACKET_POKER_TOURNEY_SELECT

PacketFactory[PACKET_POKER_TOURNEY_SELECT] = PacketPokerTourneySelect

########################################
PACKET_POKER_TOURNEY = 211
PacketNames[PACKET_POKER_TOURNEY] = "POKER_TOURNEY"

class PacketPokerTourney(Packet):
    
    type = PACKET_POKER_TOURNEY
    format = "!IHIBHHB"
    format_size = calcsize(format)

    def __init__(self, *args, **kwargs):
        self.name = kwargs.get("name", "noname")
        self.description_short = kwargs.get("description_short", "nodescription_short")
        self.variant = kwargs.get("variant", "holdem")
        self.state = kwargs.get("state", "announced")
        self.serial = kwargs.get("serial", 0)
        self.buy_in = kwargs.get("buy_in", 10)
        self.start_time = kwargs.get("start_time", 0)
        self.sit_n_go = kwargs.get("sit_n_go", 'y')
        self.players_quota = kwargs.get("players_quota", 0)
        self.registered = kwargs.get("registered", 0)
        self.custom_money = kwargs.get("custom_money", 'n')
        if self.custom_money == 1: self.custom_money = 'y'
        if self.custom_money == 0: self.custom_money = 'n'

    def pack(self):
        block = Packet.pack(self)
        block += pack(PacketPokerTourney.format, self.serial, self.buy_in, self.start_time, (self.sit_n_go == 'y' and 1 or 0), self.players_quota, self.registered, (self.custom_money == 'y' and 1 or 0))
        block += self.packstring(self.description_short)
        block += self.packstring(self.variant)
        block += self.packstring(self.state)
        block += self.packstring(self.name)
        return block

    def unpack(self, block):
        block = Packet.unpack(self, block)
        (self.serial, self.buy_in, self.start_time, self.sit_n_go, self.players_quota, self.registered, self.custom_money) = unpack(PacketPokerTourney.format, block[:PacketPokerTourney.format_size])
        self.sit_n_go = self.sit_n_go and 'y' or 'n'
        self.custom_money = self.custom_money and 'y' or 'n'
        block = block[PacketPokerTourney.format_size:]
        (block, self.description_short) = self.unpackstring(block)
        (block, self.variant) = self.unpackstring(block)
        (block, self.state) = self.unpackstring(block)
        (block, self.name) = self.unpackstring(block)
        return block

    def calcsize(self):
        return Packet.calcsize(self) + PacketPokerTourney.format_size + self.calcsizestring(self.description_short) + self.calcsizestring(self.variant) + self.calcsizestring(self.state) + self.calcsizestring(self.name)

    def __str__(self):
        return Packet.__str__(self) + "\n\tserial = %s, name = %s, description_short = %s, variant = %s, state = %s, buy_in = %s, start_time = %s, sit_n_go = %s, players_quota = %s, registered = %s, custom_money = %s " % ( self.serial, self.name, self.description_short, self.variant, self.state, self.buy_in, strftime("%Y/%m/%d %H:%M", gmtime(self.start_time)), self.sit_n_go, self.players_quota, self.registered, self.custom_money )
    
PacketFactory[PACKET_POKER_TOURNEY] = PacketPokerTourney

########################################

PACKET_POKER_TOURNEY_INFO = 212
PacketNames[PACKET_POKER_TOURNEY_INFO] = "POKER_TOURNEY_INFO"

class PacketPokerTourneyInfo(PacketPokerTourney):

    type = PACKET_POKER_TOURNEY_INFO
    reason = ""

    def __init__(self, *args, **kwargs):
        self.description_long = kwargs.get("description_long", "no long description")
        PacketPokerTourney.__init__(self, *args, **kwargs)
        
    def pack(self):
        return PacketPokerTourney.pack(self) + self.packstring(self.description_long)

    def unpack(self, block):
        block = PacketPokerTourney.unpack(self, block)
        (block, self.description_long) = self.unpackstring(block)
        return block
    
    def calcsize(self):
        return PacketPokerTourney.calcsize(self) + self.calcsizestring(self.description_long)

    def __str__(self):
        return PacketPokerTourney.__str__(self) + " description_long = %s" % self.description_long

PacketFactory[PACKET_POKER_TOURNEY_INFO] = PacketPokerTourneyInfo

########################################

PACKET_POKER_TOURNEY_LIST = 213
PacketNames[PACKET_POKER_TOURNEY_LIST] = "POKER_TOURNEY_LIST"

class PacketPokerTourneyList(PacketList):
    """\
Semantics: a list of PACKET_POKER_TOURNEY packets sent as a
response to a PACKET_POKER_SELECT request.

Direction: server  => client

packets: a list of PACKET_POKER_TOURNEY packets.
"""
    
    type = PACKET_POKER_TOURNEY_LIST

    format = "!II"
    format_size = calcsize(format)

    def __init__(self, *args, **kwargs):
        self.players = kwargs.get("players", 0)
        self.tourneys = kwargs.get("tourneys", 0)
        PacketList.__init__(self, *args, **kwargs)

    def pack(self):
        return PacketList.pack(self) + pack(PacketPokerTourneyList.format, self.players, self.tourneys)

    def unpack(self, block):
        block = PacketList.unpack(self, block)
        (self.players, self.tourneys) = unpack(PacketPokerTourneyList.format, block[:PacketPokerTourneyList.format_size])
        return block[PacketPokerTourneyList.format_size:]

    def calcsize(self):
        return PacketList.calcsize(self) + PacketPokerTourneyList.format_size

    def __str__(self):
        return PacketList.__str__(self) + "\n\tplayers = %d, tourneys = %d" % ( self.players, self.tourneys )

PacketFactory[PACKET_POKER_TOURNEY_LIST] = PacketPokerTourneyList

########################################

PACKET_POKER_TOURNEY_REQUEST_PLAYERS_LIST = 214
PacketNames[PACKET_POKER_TOURNEY_REQUEST_PLAYERS_LIST] = "POKER_TOURNEY_REQUEST_PLAYERS_LIST"

class PacketPokerTourneyRequestPlayersList(PacketPokerId):
    """\
Semantics: client request the player list of the tourney "game_id".

Direction: client => server

game_id: integer uniquely identifying a game.
"""

    type = PACKET_POKER_TOURNEY_REQUEST_PLAYERS_LIST

PacketFactory[PACKET_POKER_TOURNEY_REQUEST_PLAYERS_LIST] = PacketPokerTourneyRequestPlayersList

########################################

PACKET_POKER_TOURNEY_REGISTER = 215
PacketNames[PACKET_POKER_TOURNEY_REGISTER] = "POKER_TOURNEY_REGISTER"

class PacketPokerTourneyRegister(PacketPokerId):

    DOES_NOT_EXIST = 1
    ALREADY_REGISTERED = 2
    REGISTRATION_REFUSED = 3
    NOT_ENOUGH_MONEY = 4
    SERVER_ERROR = 5
    
    type = PACKET_POKER_TOURNEY_REGISTER

PacketFactory[PACKET_POKER_TOURNEY_REGISTER] = PacketPokerTourneyRegister

########################################

PACKET_POKER_TOURNEY_UNREGISTER = 216
PacketNames[PACKET_POKER_TOURNEY_UNREGISTER] = "POKER_TOURNEY_UNREGISTER"

class PacketPokerTourneyUnregister(PacketPokerId):

    DOES_NOT_EXIST = 1
    NOT_REGISTERED = 2
    TOO_LATE = 3
    SERVER_ERROR = 4

    type = PACKET_POKER_TOURNEY_UNREGISTER

PacketFactory[PACKET_POKER_TOURNEY_UNREGISTER] = PacketPokerTourneyUnregister

########################################

PACKET_POKER_ANIMATION_DEALER_CHANGE = 217
PacketNames[PACKET_POKER_ANIMATION_DEALER_CHANGE] = "POKER_PLAYER_DEALER_CHANGE"

class PacketPokerAnimationDealerChange(PacketPokerId):
    """\
"""
    type = PACKET_POKER_ANIMATION_DEALER_CHANGE

    def __init__(self, *args, **kwargs):
        if kwargs.has_key("state"):
            self.state = kwargs["state"]
        
        PacketPokerId.__init__(self, *args, **kwargs)

    def __str__(self):
        return PacketPokerId.__str__(self) + " serial = %d, state %s" % ( self.serial , self.state )
    
PacketFactory[PACKET_POKER_ANIMATION_DEALER_CHANGE] = PacketPokerAnimationDealerChange

########################################

PACKET_POKER_ANIMATION_DEALER_BUTTON = 218
PacketNames[PACKET_POKER_ANIMATION_DEALER_BUTTON] = "POKER_PLAYER_DEALER_BUTTON"

class PacketPokerAnimationDealerButton(PacketPokerId):
    """\
"""
    type = PACKET_POKER_ANIMATION_DEALER_BUTTON

    def __init__(self, *args, **kwargs):
        if kwargs.has_key("state"):
            self.state = kwargs["state"]
        
        PacketPokerId.__init__(self, *args, **kwargs)

    def __str__(self):
        return PacketPokerId.__str__(self) + " serial = %d, state %s" % ( self.serial , self.state )
    
PacketFactory[PACKET_POKER_ANIMATION_DEALER_BUTTON] = PacketPokerAnimationDealerButton

########################################

PACKET_POKER_TOURNEY_PLAYERS_LIST = 219
PacketNames[PACKET_POKER_TOURNEY_PLAYERS_LIST] = "POKER_TOURNEY_PLAYERS_LIST"

class PacketPokerTourneyPlayersList(PacketPokerPlayersList):

    type = PACKET_POKER_TOURNEY_PLAYERS_LIST

PacketFactory[PACKET_POKER_TOURNEY_PLAYERS_LIST] = PacketPokerTourneyPlayersList

########################################

PACKET_POKER_BEGIN_ROUND = 220
PacketNames[PACKET_POKER_BEGIN_ROUND] = "POKER_BEGIN_ROUND"

class PacketPokerBeginRound(PacketPokerId):
    """\
Semantics: opens a betting round for game "game_id".

Direction: client <=> client

Context: inferred when the client knows that a betting round will
begin although it does not yet received information from the server to
initialize it. Paying the blind / ante is not considered a betting
round. It follows the POKER_END_ROUND packet, either
immediatly if the server has no delay between betting rounds
or later if the server waits a few seconds between two betting
rounds.

Example applied to holdem:

         state

         blind     END
BEGIN    preflop   END
BEGIN    flop      END
BEGIN    turn      END
BEGIN    river
         end

game_id: integer uniquely identifying a game.
"""
    
    type = PACKET_POKER_BEGIN_ROUND

PacketFactory[PACKET_POKER_BEGIN_ROUND] = PacketPokerBeginRound

########################################

PACKET_POKER_HAND_HISTORY = 221
PacketNames[PACKET_POKER_HAND_HISTORY] = "POKER_HAND_HISTORY"

class PacketPokerHandHistory(PacketPokerId):
    type = PACKET_POKER_HAND_HISTORY

    NOT_FOUND = 1
    FORBIDDEN = 2
    
    def __init__(self, *args, **kwargs):
        self.history = kwargs.get("history", "")
        self.serial2name = kwargs.get("serial2name", "")
        PacketPokerId.__init__(self, *args, **kwargs)

    def pack(self):
        return PacketPokerId.pack(self) + self.packstring(self.history) + self.packstring(self.serial2name)

    def unpack(self, block):
        block = PacketPokerId.unpack(self, block)
        (block, self.history) = self.unpackstring(block)
        (block, self.serial2name) = self.unpackstring(block)
        return block

    def calcsize(self):
        return PacketPokerId.calcsize(self) + self.calcsizestring(self.history) + self.calcsizestring(self.serial2name)

    def __str__(self):
        return PacketPokerId.__str__(self) + " history = %s, serial2name = %s" % ( self.history, self.serial2name )

PacketFactory[PACKET_POKER_HAND_HISTORY] = PacketPokerHandHistory

########################################

PACKET_POKER_CURRENT_GAMES = 222
PacketNames[PACKET_POKER_CURRENT_GAMES] = "POKER_CURRENT_GAMES"

class PacketPokerCurrentGames(Packet):

    type = PACKET_POKER_CURRENT_GAMES

    format = "!B"
    format_size = calcsize(format)
    format_element = "!I"

    def __init__(self, *args, **kwargs):
        self.game_ids = kwargs.get("game_ids", [])
        self.count = kwargs.get("count", 0)

    def pack(self):
        return Packet.pack(self) + self.packlist(self.game_ids, PacketPokerCurrentGames.format_element) + pack(PacketPokerCurrentGames.format, self.count)
        
    def unpack(self, block):
        block = Packet.unpack(self, block)
        (block, self.game_ids) = self.unpacklist(block, PacketPokerCurrentGames.format_element)
        (self.count,) = unpack(PacketPokerCurrentGames.format, block[:PacketPokerCurrentGames.format_size])
        return block[PacketPokerCurrentGames.format_size:]

    def calcsize(self):
        return Packet.calcsize(self) + self.calcsizelist(self.game_ids, PacketPokerCurrentGames.format_element) + PacketPokerCurrentGames.format_size

    def __str__(self):
        return Packet.__str__(self) + " count = %d, game_ids = %s" % ( self.count, self.game_ids )

PacketFactory[PACKET_POKER_CURRENT_GAMES] = PacketPokerCurrentGames

######################################## Display packet

PACKET_POKER_END_ROUND_LAST = 223
PacketNames[PACKET_POKER_END_ROUND_LAST] = "POKER_END_ROUND_LAST"

class PacketPokerEndRoundLast(PacketPokerId):
    
    type = PACKET_POKER_END_ROUND_LAST

PacketFactory[PACKET_POKER_END_ROUND_LAST] = PacketPokerEndRoundLast


######################################## Stop or Start animation

PACKET_POKER_PYTHON_ANIMATION = 224
PacketNames[PACKET_POKER_PYTHON_ANIMATION] = "POKER_PYTHON_ANIMATION"

class PacketPokerPythonAnimation(PacketPokerId):
    
    type = PACKET_POKER_PYTHON_ANIMATION

    def __init__(self, *args, **kwargs):
        self.animation =  kwargs.get("animation", "none")
        
        PacketPokerId.__init__(self, *args, **kwargs)

PacketFactory[PACKET_POKER_PYTHON_ANIMATION] = PacketPokerPythonAnimation


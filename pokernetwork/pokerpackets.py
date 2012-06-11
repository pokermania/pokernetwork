#
# Copyright (C) 2006 - 2010 Loic Dachary <loic@dachary.org>
# Copyright (C)             2008, 2009 Bradley M. Kuhn <bkuhn@ebb.org>
# Copyright (C) 2004, 2005, 2006       Mekensleep <licensing@mekensleep.com>
#                                      24 rue vieille du temple 75004 Paris
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
#  Loic Dachary <loic@gnu.org>
#  Bradley M. Kuhn <bkuhn@ebb.org> (2008-)
#  Cedric Pinson <cpinson@freesheep.org> (2004-2006)
#  Henry Precheur <henry@precheur.org> (2004)
#
#     Theory of operations.
#
#     When the client send packets, the reply packets sent by the
#     server are listed in the packet documentation.
#     
#     How to tell the server that the client is alive every 10 seconds ?
#        If and only if the client does not send any packet during
#        more than 10 sec, you must send a PACKET_PING
#
#     PACKET_PING
#
#     How to cash in ?
#
#     POKER_CASH_IN
#
#     How to sit at a cash game table ?
#     
#     PACKET_POKER_TABLE_JOIN
#     PACKET_POKER_SEAT
#     PACKET_POKER_BUY_IN
#     PACKET_POKER_AUTO_BLIND_ANTE
#     PACKET_POKER_SIT
#
#     How to quickly get to a cash game table that fits certain criteria?
#
#     PACKET_POKER_TABLE_PICKER
#
#     How to leave a cash game table ?
#
#     PACKET_POKER_TABLE_QUIT
#
#     What to expect when watching a table ? 
#     
#     PACKET_POKER_PLAYER_ARRIVE
#     PACKET_POKER_PLAYER_STATS
#     PACKET_POKER_PLAYER_CHIPS
#     PACKET_POKER_PLAYER_SIT
#     PACKET_POKER_PLAYER_SIT_OUT
#     PACKET_POKER_CHAT
#     PACKET_POKER_PLAYER_LEAVE
#
#     What to expect at all times ?
#
#     PACKET_POKER_MESSAGE
#
#     How do I get the list of tournaments ?
#
#     PACKET_POKER_TOURNEY_SELECT
#
#     How do I get the list of players registered in a tournament ?
#
#     PACKET_POKER_TOURNEY_REQUEST_PLAYERS_LIST
#
#     What to expect while a hand is being played ?
#
#     PACKET_POKER_IN_GAME
#     PACKET_POKER_DEALER
#     PACKET_POKER_START
#     PACKET_POKER_CANCELED
#     PACKET_POKER_STATE
#     PACKET_POKER_POSITION
#     PACKET_POKER_BLIND
#     PACKET_POKER_ANTE
#     PACKET_POKER_CALL
#     PACKET_POKER_RAISE
#     PACKET_POKER_FOLD
#     PACKET_POKER_CHECK
#     PACKET_POKER_RAKE
#     PACKET_POKER_WIN
#
#     What to expect while participating in a hand ?
#
#     PACKET_POKER_BLIND_REQUEST
#     PACKET_POKER_ANTE_REQUEST
#     PACKET_POKER_MUCK_REQUEST
#     PACKET_POKER_SELF_IN_POSITION
#     PACKET_POKER_SELF_LOST_POSITION
#
#     What to send after receiving PACKET_POKER_SELF_IN_POSITION ?
#
#     PACKET_POKER_CALL
#     PACKET_POKER_RAISE
#     PACKET_POKER_FOLD
#     PACKET_POKER_CHECK
#
#     What to send after receiving PACKET_POKER_MUCK_REQUEST ?
#
#     PACKET_POKER_MUCK_ACCEPT or
#     PACKET_POKER_MUCK_DENY
#     
#     How to list tournaments ?
#     
#     PACKET_POKER_TOURNEY_SELECT
#
#     What to expect in response to PACKET_POKER_TOURNEY_SELECT ? 
#
#     PACKET_POKER_TOURNEY_LIST containing
#       PACKET_POKER_TOURNEY packets
#
#     How to list players registered in a tournament ? 
#
#     PACKET_POKER_TOURNEY_REQUEST_PLAYERS_LIST
#
#     What to expect in response to PACKET_POKER_TOURNEY_REQUEST_PLAYERS_LIST ? 
#
#     PACKET_POKER_TOURNEY_PLAYERS_LIST
#  
#     How to register to a tournament ?
#
#     PACKET_POKER_TOURNEY_REGISTER
#
#     What to expect in response to PACKET_POKER_TOURNEY_REGISTER ? 
#
#     PACKET_POKER_TOURNEY_REGISTER if success (the same that was sent)
#     PACKET_ERROR if failure
#
#     How to unregister to a tournament ?
#
#     PACKET_POKER_TOURNEY_UNREGISTER
#
#     What to expect in response to PACKET_POKER_TOURNEY_UNREGISTER ? 
#
#     PACKET_POKER_TOURNEY_UNREGISTER if success (the same that was sent)
#     PACKET_ERROR if failure
#
#     What is sent to the tournament player that was busted out of a 
#     tournament (or is the winner) ?  
# 
#     PACKET_POKER_TOURNEY_RANK
#
#     What is sent to the player when the tournament starts ? 
#
#     What should the client expect when moved to another
#       table during a tournament ?
#
#     PACKET_POKER_TABLE_MOVE (or PACKET_POKER_PLAYER_LEAVE if explain mode)
#     (and PACKET_POKER_SEATS if explain mode)
#     
#     How to instruct the server to wait for the client before dealing
#     the next hand ? 
# 
#     PACKET_POKER_PROCESSING_HAND
#
#     How to tell the server that the client has finished displaying the
#     current hand and can deal the next one ?
#
#     PACKET_POKER_READY_TO_PLAY
# 
#     What should the client expect when a tournament break begins/ends?
#
#     POKER_TABLE_TOURNEY_BREAK_BEGIN
#     POKER_TABLE_TOURNEY_BREAK_END

import sys
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
""" #pragma: no cover

from struct import pack, unpack, calcsize
from types import IntType, LongType
from pokernetwork.packets import *

########################################

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

    info = Packet.info + (
        ('seats', [], 'Il'),
        ('game_id', 0, 'I'),
        )
    
Packet.infoDeclare(globals(), PacketPokerSeats, Packet, "POKER_SEATS", 50) # 50 # 0x32
########################################

class PacketPokerId(PacketSerial):
    """
    abstract packet with game id and serial
    """

    info = PacketSerial.info + (
        ('game_id', 0, 'I'), 
        )
        
Packet.infoDeclare(globals(), PacketPokerId, Packet, "POKER_ID", 51) # 51 # 0x33
########################################

class PacketPokerMessage(PacketPokerId):
    """
    server => client
    Informative messages
    """

    info = PacketPokerId.info + (
        ('string', '', 's' ), 
        )
        
Packet.infoDeclare(globals(), PacketPokerMessage, Packet, "POKER_MESSAGE", 52) # 52 # 0x34
########################################

class PacketPokerError(PacketPokerId):
    """
    Packet describing an error
    """

    info = PacketPokerId.info + (
        ('message', 'no message', 's'),
        ('code', 0, 'I'),
        ('other_type', 53, 'B'),
        )

Packet.infoDeclare(globals(), PacketPokerError, Packet, "POKER_ERROR", 53) # 53 # 0x35
########################################

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

    info = Packet.info + (
        ('game_id', 0, 'I'),
        ('position', -1, 'b'),
        ('serial', 0, 'I'), 
        )
    
Packet.infoDeclare(globals(), PacketPokerPosition, Packet, "POKER_POSITION", 54) # 54 # 0x36
########################################

class PacketPokerInt(PacketPokerId):
    """
    base class for a int coded amount
    """

    info = PacketPokerId.info + (
        ('amount', 0, 'I'), 
        )
    
Packet.infoDeclare(globals(), PacketPokerInt, Packet, "POKER_INT", 55) # 55 # 0x37
########################################

class PacketPokerBet(PacketPokerInt):
    """
    base class for raise. It is not used. To bet use PokerRaise instead.
    """

Packet.infoDeclare(globals(), PacketPokerBet, Packet, "POKER_BET", 56) # 56 # 0x38
########################################

class PacketPokerFold(PacketPokerId):
    """\
Semantics: the "serial" player folded.

Direction: server <=> client

serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

Packet.infoDeclare(globals(), PacketPokerFold, Packet, "POKER_FOLD", 57) # 57 # 0x39
########################################

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

serial: the unique number associated to the user.
game_id: integer uniquely identifying a game.
string: state of the game.
"""

    info = PacketPokerId.info + (
        ('string', '', 's'), 
        )
    
Packet.infoDeclare(globals(), PacketPokerState, Packet, "POKER_STATE", 58) # 58 # 0x3a
########################################

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

    info = PacketPokerId.info + (
        ('serials', [], 'Il'),
        )
    
Packet.infoDeclare(globals(), PacketPokerWin, Packet, "POKER_WIN", 59) # 59 # 0x3b
########################################

class PacketPokerCards(PacketPokerId):
    """
    base class for player / board / best cards
    """

    info = PacketPokerId.info + (
        ('cards', [], 'Bl'), 
        )
    
Packet.infoDeclare(globals(), PacketPokerCards, Packet, "POKER_CARDS", 60) # 60 # 0x3c
########################################

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

Packet.infoDeclare(globals(), PacketPokerPlayerCards, Packet, "POKER_PLAYER_CARDS", 61) # 61 # 0x3d
########################################

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

Packet.infoDeclare(globals(), PacketPokerBoardCards, Packet, "POKER_BOARD_CARDS", 62) # 62 # 0x3e
########################################

class PacketPokerChips(PacketPokerId):
    """base class"""

    info = PacketPokerId.info + ( ('bet', 0, 'Q'), )
    
Packet.infoDeclare(globals(), PacketPokerChips, Packet, "POKER_CHIPS", 63) # 63 # 0x3f
########################################

class PacketPokerPlayerChips(PacketPokerChips):
    """\
Semantics: the "money" of the player "serial" engaged in
game "game_id" and the "bet" currently wagered by the player, if any.

Direction: server  => client

Context: this packet is infered each time the bet or the chip
stack of a player is modified.

bet: the number of chips wagered by the player for the current betting round.
money: the number of chips available to the player for this game.
serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

    info = PacketPokerChips.info + (
        ('money', 0, 'Q'),
        )

Packet.infoDeclare(globals(), PacketPokerPlayerChips, Packet, "POKER_PLAYER_CHIPS", 64) # 64 # 0x40
########################################

class PacketPokerCheck(PacketPokerId):
    """\
Semantics: the "serial" player checked in game
"game_id".

Direction: server <=> client

serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

Packet.infoDeclare(globals(), PacketPokerCheck, Packet, "POKER_CHECK", 65) # 65 # 0x41
########################################

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

    info = PacketPokerId.info + (
        ('hands_count', 0, 'I'),
        ('time', 0, 'I'),
        ('hand_serial', 0, 'I'),
        ('level', 0, 'B'),
        )

Packet.infoDeclare(globals(), PacketPokerStart, Packet, "POKER_START", 66) # 66 # 0x42
########################################

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

Direction: server => client

players: list of serials of players participating in the hand.
game_id: integer uniquely identifying a game.
"""

    info = PacketPokerId.info + (
        ('players', [], 'Il'), 
        )
    
Packet.infoDeclare(globals(), PacketPokerInGame, Packet, "POKER_IN_GAME", 67) # 67 # 0x43
########################################

class PacketPokerCall(PacketPokerId):
    """\
Semantics: the "serial" player called in game "game_id".

Direction: server <=> client

serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

Packet.infoDeclare(globals(), PacketPokerCall, Packet, "POKER_CALL", 68) # 68 # 0x44
########################################

class PacketPokerRaise(PacketPokerBet):
    """\
Semantics: the "serial" player raised "amount" chips in
game "game_id".

Direction: server <=> client

Context: the client infers a PACKET_POKER_BET_LIMIT packet each
time the position changes.

amount: the number of chips for the raise. A value of all 0 means the lowest possible raise.
     A value larger than the maximum raise will be clamped by
     the server.
serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

Packet.infoDeclare(globals(), PacketPokerRaise, Packet, "POKER_RAISE", 69) # 69 # 0x45
########################################

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

    info = Packet.info + (
        ('game_id', 0, 'I'),
        ('dealer', -1, 'b'),
        ('previous_dealer', -1, 'b'),
        )

Packet.infoDeclare(globals(), PacketPokerDealer, Packet, "POKER_DEALER", 70) # 70 # 0x46
########################################

class PacketPokerTableJoin(PacketPokerId):
    """\
Semantics: player "serial" wants to become an observer
of the game "game_id".

There are three possible outcomes for the client in response to a
PacketPokerTableJoin():

  (0) In the case that the join is completely successful, or if the player
      had already joined the table, the following packets are sent:

          PACKET_POKER_TABLE
          PACKET_POKER_BATCH_MODE
          for each player in the game:
               PACKET_POKER_PLAYER_ARRIVE
          if the player is playing:
                PACKET_POKER_PLAYER_CHIPS
          if the player is sit:
                PACKET_POKER_SIT
          PACKET_POKER_SEATS
          if the game is running:
                the exact packet sequence that lead to the current state
                of the game. Varies according to the game.
          PACKET_POKER_STREAM_MODE

      Note clearly that if the player had already previously joined the
      table, the packets above will be sent as if the player just joined.
      However, in that case, the packet will have no side effect.


   (1) If the the player was unable to join the table specifically that
       the server has reached the maximum number of joined players, two
       packets will be sent to the client, the second of which is
       deprecated:

        (a) the following packet (recommended way of testing for failure):
            PacketPokerError(code      = PacketPokerTableJoin.FULL,
                            message   = "This server has too many seated players and observers.",
                           other_type = PACKET_POKER_TABLE_JOIN,
                           serial     = <player's serial id>,
                           game_id    = <id of the table>)

        (b) a packet, PACKET_POKER_TABLE, with serial 0 will be sent.  It
            will contain no meaningful information.  (THIS BEHAVIOR IS
            DEPRECATED, and is left only for older clients.
            New clients should not rely on this behavior.)

  (2) If the player cannot join the table for any reason (other than the
      table is FULL (as per (1) above), two packets will be sent to the
      client, one of which is deprecated:

       (a) the following packet (recommended way of testing for failure):
           PacketPokerError(code      = PacketPokerTableJoin.GENERAL_FAILURE,
                            message   = <some string of non-zero length, for use
                                        in displaying to the user>,
                           other_type = PACKET_POKER_TABLE_JOIN,
                           serial     = <player's serial id>,
                           game_id    = 0)

       (b) a packet, PACKET_POKER_TABLE, with serial 0 will be sent.  It
           will contain no meaningful information.  (THIS BEHAVIOR IS
           DEPRECATED, and is left only for older clients.
           New clients should not rely on this behavior.)

Direction: server <= client

serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

    FULL = 1
    GENERAL_FAILURE = 2
    NOT_JOINED = 1001

Packet.infoDeclare(globals(), PacketPokerTableJoin, Packet, "POKER_TABLE_JOIN", 71) # 71 # 0x47
########################################

class PacketPokerTableSelect(PacketString):
    """\
Semantics: request the list of tables matching the "string" constraint.
The answer is a possibly empty PACKET_POKER_TABLE_LIST packet.

Direction: server <=  client

string: currency<tabulation>variant
        Examples: 1 holdem selects all holdem tables using this currency
        The specials value "my" restricts the search to the tables
        in which the player id attached to the connection is playing.
"""

Packet.infoDeclare(globals(), PacketPokerTableSelect, Packet, "POKER_TABLE_SELECT", 72) # 72 # 0x48
########################################
class PacketPokerTable(Packet):
    """\
Semantics: the full description of a poker game. When sent
to the server, act as a request to create the corresponding
game. When sent by the server, describes an existing poker
game.

The answer sent to the client will be the same as the answer
sent when receiving a PacketPokerTableJoin packet.

Direction: server <=> client

Display information:
# 10 seats (P01 to P10)
# a dealer button (D)
# each player has two chip stacks displayed on the table
## the chips that are not engaged in the game (M)
## the chips that were bet during this betting round (B)
# each player two places for cards
## up to 5 cards hidden in his hand (H)
## up to 7 cards on the table in front of him (some up some down) (V)
# 5 community cards are displayed face up in the middle (C)
# up to 9 pots are in the middle, each for a player who is allin (P1 to P9)
# at showdown the winning hands are
## two hands for high / low variants (colors on H, V or C)
## as many winning hands per allin player
{{{
        HHHHH   HHHHH    HHHHH   HHHHH
         P09     P10      P01     P02
       VVVVVVV VVVVVVV  VVVVVVV VVVVVVV
         B M     B M      B M     B M
  HHHHH                               HHHHH
   P08 M B        CCCCC            B M P03
 VVVVVVV P1 P2 P3 P4 P5 P6 P7 P8 P9  VVVVVVV

         B M     B M      B M     B M D
       VVVVVVV VVVVVVV   VVVVVVV VVVVVVV
         P07     P06       P05     P04
        HHHHH   HHHHH     HHHHH   HHHHH
}}}

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
players: the number of players who joined the table and are seated
observers: the number of players who joined (as in PACKET_POKER_TABLE_JOIN)
           the table but are not seated.
waiting: the number of players in the waiting list.
player_timeout: the number of seconds after which a player in position is forced to
         play (by folding).
muck_timeout: the number of seconds after which a player is forced to muck.
currency_serial: int currency id
skin: name of the level model to use
reason: string representing the reason that this packet is being sent to
        the client.  Possible values are ("", "TableList", "TablePicker",
        "TourneyMove", "TourneyStart", "TableJoin", "TableCreate", "HandReplay")
"""

    REASON_TABLE_LIST    = "TableList"
    REASON_TABLE_PICKER  = "TablePicker"
    REASON_TOURNEY_MOVE  = "TourneyMove"
    REASON_TOURNEY_START = "TourneyStart"
    REASON_TABLE_JOIN    = "TableJoin"
    REASON_TABLE_CREATE  = "TableCreate"
    REASON_HAND_REPLAY   = "HandReplay"
    REASON_NONE          = ""

    info = Packet.info + (
        ('id', 0, 'I'),
        ('seats', 10, 'B'),
        ('average_pot', 0, 'I'),
        ('hands_per_hour', 0, 'H'),
        ('percent_flop', 0, 'B'),
        ('players', 0, 'B'),
        ('observers', 0, 'H'),
        ('waiting', 0, 'B'),
        ('player_timeout', 0, 'H'),
        ('muck_timeout', 0, 'H'),
        ('currency_serial', 0, 'I'),
        ('name', 'noname', 's'),
        ('variant', 'holdem', 's'),
        ('betting_structure', '2-4-limit', 's'),
        ('skin', 'default', 's'),
        ('reason', '', 's'),
        ('tourney_serial', 0, 'I'),
        ('player_seated',-1,'no net')
        )
    
Packet.infoDeclare(globals(),PacketPokerTable, Packet, "POKER_TABLE", 73) # 73 # 0x49
########################################

class PacketPokerTableList(PacketList):
    """\
Semantics: a list of PACKET_POKER_TABLE packets sent as a
response to a PACKET_POKER_SELECT request.

Direction: server  => client

packets: a list of PACKET_POKER_TABLE packets.
"""

    info = PacketList.info + (
        ('players', 0, 'I'),
        ('tables', 0, 'I'),
        )

Packet.infoDeclare(globals(),PacketPokerTableList, Packet, "POKER_TABLE_LIST", 74) # 74 # 0x4a
########################################

class PacketPokerSit(PacketPokerId):
    """\
Semantics: the player "serial" is willing to participate in
the game "game_id".

Direction: server <=> client

Context: this packet must occur after getting a seat for the
game (i.e. a PACKET_POKER_SEAT is honored by the server). A
number of PACKET_POKER_SIT packets are inferred from the
 PACKET_POKER_IN_GAME packet. The server will broadcast to
all players and observers the PACKET_POKER_SIT in case of
success. The server will not send anything back if an error
occurs.

serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

Packet.infoDeclare(globals(),PacketPokerSit, Packet, "POKER_SIT", 75) # 75 # 0x4b
########################################

class PacketPokerTableDestroy(PacketPokerId):
    """destroy"""

Packet.infoDeclare(globals(),PacketPokerTableDestroy, Packet, "POKER_TABLE_DESTROY", 76) # 76 # 0x4c
########################################

class PacketPokerTimeoutWarning(PacketPokerId):
    """\
Semantics: the player "serial" is taking too long to play and will
be folded automatically shortly in the game "game_id".

Direction: server  => client

serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

    info = PacketPokerId.info + (
        ('timeout', sys.maxint, 'I'),
        ('when', -1, 'no net'),
        )

Packet.infoDeclare(globals(),PacketPokerTimeoutWarning, Packet, "POKER_TIMEOUT_WARNING", 77) # 77 # 0x4d
########################################

class PacketPokerTimeoutNotice(PacketPokerId):
    """\
Semantics: the player "serial" is took too long to play and has
been folded in the game "game_id".

Direction: server  => client

serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

Packet.infoDeclare(globals(),PacketPokerTimeoutNotice, Packet, "POKER_TIMEOUT_NOTICE", 78) # 78 # 0x4e
########################################

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
    ROLE_PLAY = 1

    info = PacketPokerId.info + ( ('seat', -1, 'b'), )

Packet.infoDeclare(globals(),PacketPokerSeat, Packet, "POKER_SEAT", 79) # 79 # 0x4f
########################################

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

    info = PacketPokerSeat.info + ( ('to_game_id', sys.maxint, 'I'), )

Packet.infoDeclare(globals(),PacketPokerTableMove, Packet, "POKER_TABLE_MOVE", 80) # 80 # 0x50
########################################

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

Packet.infoDeclare(globals(),PacketPokerPlayerLeave, Packet, "POKER_PLAYER_LEAVE", 81) # 81 # 0x51
########################################

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

Packet.infoDeclare(globals(),PacketPokerSitOut, Packet, "POKER_SIT_OUT", 82) # 82 # 0x52
########################################

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

Packet.infoDeclare(globals(), PacketPokerTableQuit, Packet, "POKER_TABLE_QUIT", 83) # 83 # 0x53
########################################

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

    info = PacketPokerId.info + ( ('amount', 0, 'I'), )

Packet.infoDeclare(globals(),PacketPokerBuyIn , Packet, "POKER_BUY_IN", 84) # 84 # 0x54
########################################

class PacketPokerRebuy(PacketPokerBuyIn):
    """\
Semantics: the player "serial" is willing to participate in
the game "game_id" with an amount equal to "amount". The server
will ensure that the "amount" fits the game constraints (i.e.
player bankroll or betting structure limits).

Direction: server <=  client.

Context: this packet must occur after a successfull PACKET_POKER_BUY_IN
The minimum/maximum rebuy are determined by the betting structure of
the game, as specified in the PACKET_POKER_TABLE packet. The player
may rebuy at any moment if he has less than the maximum amount of money
allowed by the betting structure.

amount: integer specifying the amount to bring to the game.
serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

Packet.infoDeclare(globals(),PacketPokerRebuy , Packet, "POKER_REBUY", 85) # 85 # 0x55
########################################

class PacketPokerChat(PacketPokerId):
    """\
Semantics: a text "message" sent to all players seated
at the poker table "game_id".

Direction: server  <=> client

message: a text message string (2^16 long max)
game_id: integer uniquely identifying a game.
"""

    info = PacketPokerId.info + ( ('message', '', 's'), )
   
Packet.infoDeclare(globals(),PacketPokerChat , Packet, "POKER_CHAT", 86) # 86 # 0x56
########################################

PACKET_POKER_PLAYER_INFO = 87 # 0x57 # %SEQ%
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
    
    info = PacketPokerId.info + (
        ('name', 'noname', 's'),
        ('outfit', 'random', 's'),
        ('url', 'random', 's'),
        # FIXME_PokerPlayerInfoLocale: 
        # (see also sr #2262 )
        # should "locale" be here?  It's
        #  referenced in
        #  PokerService.getPlayerInfo().  I'm the
        #  one who probably added that, but I am
        #  unclear as to why right now, but
        #  wanted to note I notced. -- bkuhn
        )
   
Packet.infoDeclare(globals(),PacketPokerPlayerInfo , Packet, "POKER_PLAYER_INFO", 87) # 87 # 0x57
########################################

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

    info = PacketPokerPlayerInfo.info + ( 
        ('blind', 'late', 'bs'),
        ('remove_next_turn', False, 'bool'),
        ('sit_out', True, 'bool'),
        ('sit_out_next_turn', False, 'bool'),
        ('auto', False, 'bool'),
        ('auto_blind_ante', False, 'bool'),
        ('wait_for', False, 'bool'),
        ('buy_in_payed', False, 'bool'),
        ('seat', None, 'Bnone'),
        )
    
Packet.infoDeclare(globals(), PacketPokerPlayerArrive, Packet, "POKER_PLAYER_ARRIVE", 88) # 88 # 0x58
########################################

PACKET_POKER_HAND_SELECT = 89 # 0x59 # %SEQ%
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

    info = PacketString.info + ( 
        ('start', 0, 'I'),
        ('count', 50, 'B'),
        )
    
Packet.infoDeclare(globals(), PacketPokerHandSelect, Packet, "POKER_HAND_SELECT", 89) # 89 # 0x59
########################################

PACKET_POKER_HAND_LIST = 90 # 0x5a # %SEQ%
PacketNames[PACKET_POKER_HAND_LIST] = "POKER_HAND_LIST"

class PacketPokerHandList(PacketPokerHandSelect):
    """\
Semantics: a list of hand serials known to the server.

Direction: server  => client

Context: reply to the PACKET_POKER_HAND_SELECT packet.

hands: list of integers uniquely identifying a hand to the server.
"""

    info = PacketPokerHandSelect.info + ( 
        ('hands', [], 'Il'),
        ('total', sys.maxint, 'I'),
        )
    
Packet.infoDeclare(globals(), PacketPokerHandList, Packet, "POKER_HAND_LIST", 90) # 90 # 0x5a
########################################

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

Packet.infoDeclare(globals(), PacketPokerHandSelectAll, Packet, "POKER_HAND_SELECT_ALL", 91) # 91 # 0x5b
########################################

class PacketPokerUserInfo(PacketSerial):
    """\
Semantics: read only user descriptive information, complement
of PACKET_POKER_PLAYER_INFO.

Direction: server  => client

Context: answer to the PACKET_POKER_GET_USER_INFO packet.

rating: server wide ELO rating.
serial: integer uniquely identifying a player.
"""

    NOT_LOGGED = 1

    info = PacketSerial.info + ( 
        ('rating', 1500, 'I'),
        ('affiliate', 0, 'I'),
        ('name', 'unknown', 's'),
        ('password', '', 's'),
        ('email', '', 's'),
        ('money', {}, 'money'),
        )

Packet.infoDeclare(globals(), PacketPokerUserInfo, Packet, "POKER_USER_INFO", 92) # 92 # 0x5c
########################################

class PacketPokerGetUserInfo(PacketSerial):
    """\
Semantics: request the read only descriptive information
for player "serial".

Direction: server <=  client

Context: a user must first login (PACKET_LOGIN) successfully
before sending this packet.

serial: integer uniquely identifying a player.
"""

Packet.infoDeclare(globals(), PacketPokerGetUserInfo, Packet, "POKER_GET_USER_INFO", 93) # 93 # 0x5d
########################################

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

Packet.infoDeclare(globals(), PacketPokerAnte, Packet, "POKER_ANTE", 94) # 94 # 0x5e
########################################

PACKET_POKER_BLIND = 95 # 0x5f # %SEQ%
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

    info = PacketPokerInt.info + (
        ('dead', 0, 'I'), 
        )

Packet.infoDeclare(globals(), PacketPokerBlind, Packet, "POKER_BLIND", 95) # 95 # 0x5f
########################################

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

Packet.infoDeclare(globals(), PacketPokerWaitBigBlind, Packet, "POKER_WAIT_BIG_BLIND", 96) # 96 # 0x60
########################################

class PacketPokerAutoBlindAnte(PacketPokerId):
    """\

Semantics: the player "serial" asks the server to automatically post the
           blinds or/and antes for game "game_id".  In response to this
           packet, the server sends PacketPokerAutoBlindAnte() if
           AutoBlindAnte has been successfully turned on, otherwise, it
           sends PacketPokerNoautoBlindAnte().

Direction: server <=  client

Context: by default the server will not automatically post the blinds
or/and antes. 

serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

Packet.infoDeclare(globals(), PacketPokerAutoBlindAnte, Packet, "POKER_AUTO_BLIND_ANTE", 97) # 97 # 0x61
########################################

class PacketPokerNoautoBlindAnte(PacketPokerId):
    """\
Semantics: the player "serial" asks the server to send a
           PACKET_POKER_BLIND_REQUEST or/and PACKET_POKER_ANTE_REQUEST
           when a blind or/and ante for game "game_id" must be paid.

           In response ot this packet, the server sends
           PacketPokerNoautoBlindAnte() if AutoBlindAnte has been
           successfully turned off, otherwise, it sends
           PacketPokerAautoBlindAnte().

Direction: server <=  client

Context: by default the server behaves in this way.

serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

Packet.infoDeclare(globals(), PacketPokerNoautoBlindAnte, Packet, "POKER_NOAUTO_BLIND_ANTE", 98) # 98 # 0x62
########################################

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

Packet.infoDeclare(globals(), PacketPokerCanceled, Packet, "POKER_CANCELED", 99) # 99 # 0x63
########################################

PACKET_POKER_BLIND_REQUEST = 100 # 0x64 # %SEQ%
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

    info = PacketPokerBlind.info + ( ('state', 'unknown', 's'), )

Packet.infoDeclare(globals(), PacketPokerBlindRequest, Packet, "POKER_BLIND_REQUEST", 100) # 100 # 0x64
########################################

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

Packet.infoDeclare(globals(), PacketPokerAnteRequest, Packet, "POKER_ANTE_REQUEST", 101) # 101 # 0x65
########################################

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

Packet.infoDeclare(globals(), PacketPokerAutoFold, Packet, "POKER_AUTO_FOLD", 102) # 102 # 0x66
########################################

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

    info = PacketPokerId.info + ( ('reason', '', 'bs'), )

Packet.infoDeclare(globals(), PacketPokerWaitFor, Packet, "POKER_WAIT_FOR", 103) # 103 # 0x67
########################################

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

Packet.infoDeclare(globals(), PacketPokerStreamMode, Packet, "POKER_STREAM_MODE", 104) # 104 # 0x68
########################################

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

Packet.infoDeclare(globals(), PacketPokerBatchMode, Packet, "POKER_BATCH_MODE", 105) # 105 # 0x69
########################################

class PacketPokerLookCards(PacketPokerId):
    """\
Semantics: the player "serial" is looking at his cards
in game "game_id".

Direction: server <=> client

serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

    info = PacketPokerId.info + ( ('state', 'on', 'no net'), )

Packet.infoDeclare(globals(), PacketPokerLookCards, Packet, "POKER_LOOK_CARDS", 106) # 106 # 0x6a
########################################

class PacketPokerTableRequestPlayersList(PacketPokerId):
    """\
Semantics: client request the player list of the game "game_id".

Direction: server <= client

game_id: integer uniquely identifying a game.
"""

Packet.infoDeclare(globals(), PacketPokerTableRequestPlayersList, Packet, "POKER_TABLE_REQUEST_PLAYERS_LIST", 107) # 107 # 0x6b
########################################

class PacketPokerPlayersList(Packet):
    """
Semantics: List of players participating in "game_id". 

Direction: server => client

game_id: integer uniquely identifying a game.
players: list of player serials participating in "game_id"
 for each player, a list of two numbers:
     name: name of the player
     chips: integer player chips in cent
     flag: byte 0
    """

    info = Packet.info + (
        ('game_id', 0, 'I'),
        ('players', [], 'players'),
        )


Packet.infoDeclare(globals(), PacketPokerPlayersList, Packet, "POKER_PLAYERS_LIST", 108) # 108 # 0x6c
########################################

class PacketPokerPersonalInfo(PacketPokerUserInfo):
    """\
"""

    NOT_LOGGED = 1

    info = PacketPokerUserInfo.info + ( 
        ('firstname', '', 's'),
        ('lastname', '', 's'),
        ('addr_street', '', 's'),
        ('addr_street2', '', 's'),
        ('addr_zip', '', 's'),
        ('addr_town', '', 's'),
        ('addr_state', '', 's'),
        ('addr_country', '', 's'),
        ('phone', '', 's'),
        ('gender', '', 's'),
        ('birthdate', '', 's'),
        )
    
Packet.infoDeclare(globals(), PacketPokerPersonalInfo, Packet, "POKER_PERSONAL_INFO", 109) # 109 # 0x6d
########################################

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

Packet.infoDeclare(globals(), PacketPokerGetPersonalInfo, Packet, "POKER_GET_PERSONAL_INFO", 110) # 110 # 0x6e
########################################

class PacketPokerTourneySelect(PacketString):
    """\
Semantics: request the list of tourneys matching the "string" constraint.
The answer is a PACKET_POKER_TOURNEY_LIST packet. If no tournament matches
the constraint, the list will be empty.

Direction: server <=  client

string: 1) empty string selects all tournaments
        2) a string that contains no tabulation selects
           the tournament with the same name
        3) a string with a tabulation selects all tournaments
           of a given type (sit&go or regular) that can be played
           using a given currency. The string before the tabulation
           is the name of the currency, the string after the tabulation
           distinguishes between sit&go and regular.

        Examples: 1<tabulation>sit_n_go selects all sit&go tournaments
                  using currency 1.
                  2<tabulation>regular selects all regular tournaments
                  using currency 2
"""

Packet.infoDeclare(globals(), PacketPokerTourneySelect, Packet, "POKER_TOURNEY_SELECT", 111) # 111 # 0x6f
########################################
PACKET_POKER_TOURNEY = 112 # 0x70 # %SEQ%
PacketNames[PACKET_POKER_TOURNEY] = "POKER_TOURNEY"

class PacketPokerTourney(Packet):

    info = Packet.info + ( 
        ('serial', 0, 'I'),
        ('schedule_serial', 0, 'no net'),
        ('buy_in', 10, 'I'),
        ('start_time', 0, 'I'),
        ('sit_n_go', 'y', 'cbool'),
        ('players_quota', 0, 'H'),
        ('registered', 0, 'H'),
        ('currency_serial', 0, 'I'),
        ('breaks_first', 0, 'H'),
        ('breaks_interval', 0, 'H'),
        ('breaks_duration', 0, 'H'),
        ('description_short', 'nodescription_short', 's'),
        ('variant', 'holdem', 's'),
        ('state', 'announced', 's'),
        ('name', 'noname', 's'),
        )
    
Packet.infoDeclare(globals(), PacketPokerTourney, Packet, "POKER_TOURNEY", 112) # 112 # 0x70
########################################

class PacketPokerTourneyInfo(PacketPokerTourney):

    info = PacketPokerTourney.info + (
        ('description_long', 'no long description', 's'), 
        )

Packet.infoDeclare(globals(), PacketPokerTourneyInfo, Packet, "POKER_TOURNEY_INFO", 113) # 113 # 0x71
########################################

PACKET_POKER_TOURNEY_LIST = 114 # 0x72 # %SEQ%
PacketNames[PACKET_POKER_TOURNEY_LIST] = "POKER_TOURNEY_LIST"

class PacketPokerTourneyList(PacketList):
    """\
Semantics: a list of PACKET_POKER_TOURNEY packets sent as a
response to a PACKET_POKER_SELECT request.

Direction: server  => client

packets: a list of PACKET_POKER_TOURNEY packets.
"""

    info = PacketList.info + (
        ('players', 0, 'I'),
        ('tourneys', 0, 'I'),
    )

Packet.infoDeclare(globals(), PacketPokerTourneyList, Packet, "POKER_TOURNEY_LIST", 114) # 114 # 0x72
########################################

class PacketPokerTourneyRequestPlayersList(PacketSerial):
    """\
Semantics: client request the player list of the tourney "tourney_serial".

Direction: server <= client

Context: If the tournament "tourney_serial" is among the list of known tournamens,
a PacketPokerTourneyPlayersList is returned by the server. Otherwise,
a PacketError is returned with the code set to
PacketPokerTourneyRegister.DOES_NOT_EXIST.

tourney_serial: integer uniquely identifying a tournament.
"""
    info = PacketSerial.info + (
        ('tourney_serial', 0, 'I'),
    )

Packet.infoDeclare(globals(), PacketPokerTourneyRequestPlayersList, Packet, "POKER_TOURNEY_REQUEST_PLAYERS_LIST", 115) # 115 # 0x73
########################################

class PacketPokerTourneyRegister(PacketSerial):
    """\
Semantics: register player "serial" to tournament "tourney_serial".

Direction: server <= client

If the player is registered successfully, the server will send
back the packet to the client.

If an error occurs during the tournament registration, the server
will send back

  PacketError(other_type = PACKET_POKER_TOURNEY_REGISTER)

with the "code" field name set as follows:

DOES_NOT_EXIST : the "tourney_serial" field does not match any existing
                 tournaments.
ALREADY_REGISTERED : the "serial" player is already listed as
                 a registered player in the "tourney_serial" tournament.
REGISTRATION_REFUSED : the "serial" player registration was refused
                 because the "tourney_serial" tournament is no longer in
                 the registration phase or because the players
                 quota was exceeded.
NOT_ENOUGH_MONEY : the "serial" player does not have enough money
                 to pay the "tourney_serial" tournament.
SERVER_ERROR : the server failed to register the player because the
               database is inconsistent.
VIA_SATELLITE : registration is only allowed by playing a satellite

serial: integer uniquely identifying a player.
tourney_serial: integer uniquely identifying a tournament.
"""
    DOES_NOT_EXIST = 1
    ALREADY_REGISTERED = 2
    REGISTRATION_REFUSED = 3
    NOT_ENOUGH_MONEY = 4
    SERVER_ERROR = 5
    VIA_SATELLITE = 6
    
    info = PacketSerial.info + (
        ('tourney_serial', 0, 'I'),
    )


Packet.infoDeclare(globals(), PacketPokerTourneyRegister, Packet, "POKER_TOURNEY_REGISTER", 116) # 116 # 0x74
########################################

class PacketPokerTourneyUnregister(PacketSerial):
    """\
Semantics: unregister player "serial" from tournament "tourney_serial".

Direction: server <= client

If the player is successfully unregistered, the server will send
back the packet to the client.

If an error occurs during the tournament registration, the server
will send back

  PacketError(other_type = PACKET_POKER_TOURNEY_UNREGISTER)

with the "code" field name set as follows:

DOES_NOT_EXIST : the "tourney_serial" field does not match any existing
                 tournaments.
NOT_REGISTERED : the "serial" player is not listed as
                 a registered player in the "tourney_serial" tournament.
TOO_LATE : the "serial" player cannot unregister from the tournament
           because it already started.
SERVER_ERROR : the server failed to unregister the player because the
               database is inconsistent.

serial: integer uniquely identifying a player.
tourney_serial: integer uniquely identifying a tournament.
"""

    DOES_NOT_EXIST = 1
    NOT_REGISTERED = 2
    TOO_LATE = 3
    SERVER_ERROR = 4
    
    info = PacketSerial.info + (
        ('tourney_serial', 0, 'I'),
    )


Packet.infoDeclare(globals(), PacketPokerTourneyUnregister, Packet, "POKER_TOURNEY_UNREGISTER", 117) # 117 # 0x75
########################################

class PacketPokerTourneyPlayersList(Packet):
    """
Semantics: List of players participating in tourney "serial". 

Direction: server => client

serial: integer uniquely identifying a tourney.
players: list of player serials participating in tourney "tourney_serial"
 for each player, a list of two numbers:
     name: name of the player
     chips: integer -1
     flag: byte 0
    """
    info = Packet.info + (
        ('tourney_serial', 0, 'I'),
        ('players', [], 'players'),
        )
    

Packet.infoDeclare(globals(), PacketPokerTourneyPlayersList, Packet, "POKER_TOURNEY_PLAYERS_LIST", 118) # 118 # 0x76
########################################

class PacketPokerHandHistory(PacketPokerId):

    info = PacketPokerId.info + (
        ('history', '', 's'),
        ('serial2name', '', 's'),
        )

    NOT_FOUND = 1
    FORBIDDEN = 2

Packet.infoDeclare(globals(), PacketPokerHandHistory, Packet, "POKER_HAND_HISTORY", 119) # 119 # 0x77
########################################

class PacketPokerSetAccount(PacketPokerPersonalInfo):

    NAME_TOO_SHORT = 1
    NAME_TOO_LONG = 2
    NAME_MUST_START_WITH_LETTER = 3
    NAME_NOT_ALNUM = 4
    PASSWORD_TOO_SHORT = 5
    PASSWORD_TOO_LONG = 6
    PASSWORD_NOT_ALNUM = 7
    INVALID_EMAIL = 8
    NAME_ALREADY_EXISTS = 9
    EMAIL_ALREADY_EXISTS = 10
    SERVER_ERROR = 11

Packet.infoDeclare(globals(), PacketPokerSetAccount, Packet, "POKER_SET_ACCOUNT", 120) # 120 # 0x78
########################################

class PacketPokerCreateAccount(PacketPokerSetAccount):
    """
    """
    
Packet.infoDeclare(globals(), PacketPokerCreateAccount, Packet, "POKER_CREATE_ACCOUNT", 121) # 121 # 0x79
########################################

class PacketPokerPlayerSelf(PacketPokerId):
    """
    """
    
Packet.infoDeclare(globals(), PacketPokerPlayerSelf, Packet, "POKER_PLAYER_SELF", 122) # 122 # 0x7a
########################################

class PacketPokerGetPlayerInfo(Packet):
    """
Semantics: ask the server for a PacketPokerPlayerInfo packet
describing the player that is logged in with this connection.

If the user is not logged in the following packet is returned

PacketError(code = PacketPokerGetPlayerInfo.NOT_LOGGED,
            message = "Not logged in",
            other_type = PACKET_POKER_GET_PLAYER_INFO)

If the user is logged in a PacketPokerPlayerInfo packet is sent
to the client.

Direction: server <= client
"""

    NOT_LOGGED = 1

Packet.infoDeclare(globals(), PacketPokerGetPlayerInfo, Packet, "POKER_GET_PLAYER_INFO", 123) # 123 # 0x7b
########################################

class PacketPokerRoles(PacketSerial):

    PLAY = "PLAY"
    EDIT = "EDIT"
    ROLES = [ PLAY, EDIT ]

    info = PacketSerial.info + (
        ('roles', '', 's'), 
        )

Packet.infoDeclare(globals(), PacketPokerRoles, Packet, "POKER_ROLES", 124) # 124 # 0x7c
########################################

class PacketPokerSetRole(PacketPokerRoles):
    """
Semantics: tell the server the purpose of the connection.
There are two possible roles : PLAY for a regular client
that plays poker, EDIT for a connection used to edit the
player properties but not play. There can only be one
active role per user at a given time.

The user must not be not logged in when this packet is
sent or undefined results will occur.

Direction: server <= client

roles: string PLAY or EDIT
"""

    UNKNOWN_ROLE = 1
    NOT_AVAILABLE = 2

Packet.infoDeclare(globals(), PacketPokerSetRole, Packet, "POKER_SET_ROLE", 125) # 125 # 0x7d
########################################

class PacketPokerReadyToPlay(PacketPokerId):
    """\
Semantics: the "serial" player is ready to begin a new
hand at table "game_id".

Direction: server <= client

serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

Packet.infoDeclare(globals(), PacketPokerReadyToPlay, Packet, "POKER_READY_TO_PLAY", 126) # 126 # 0x7e
########################################

class PacketPokerProcessingHand(PacketPokerId):
    """\
Semantics: the "serial" player is not ready to begin a new
hand at table "game_id" because the client is still processing
the data related to the previous hand.

Direction: server <= client

Context: should be sent by the client immediately after receiving
the POKER_START packet.

Note: the packet is ignored if the "serial" player is not at the table.

Note: because of a race condition, it will not work as expected
if the game plays too fast. For instance, if the hand finishes
before the packet POKER_PROCESSING_HAND is received by the server.
This will typically happen the first time a player gets a seat at the 
table.

serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
"""

    BUGOUS = 0

Packet.infoDeclare(globals(), PacketPokerProcessingHand, Packet, "POKER_PROCESSING_HAND", 127) # 127 # 0x7f
########################################

class PacketPokerMuckRequest(PacketPokerId):
    """\
Semantics: server is announcing a muck request to muckable players
in game "game_id". The packet is sent to all players at the table.
If a player in the list does not respond in time (the actual timeout
value depends on the server configuration and is usualy 5 seconds),
her hand will be mucked.

Direction: server <=> client
game_id: integer uniquely identifying a game.
muckable_serials: list of serials of players that are given a the choice to muck.
    """

    info = PacketPokerId.info + (
        ('muckable_serials', [], 'Il'),
        )
    
Packet.infoDeclare(globals(), PacketPokerMuckRequest, Packet, "POKER_MUCK_REQUEST", 128) # 128 # 0x80
########################################

class PacketPokerAutoMuck(PacketPokerId):
    """\
Semantics: By default the client will not be proposed to muck : the
server will always muck for him.
The client may send the PacketPokerAutoMuck to inform the server of its
muck preferences for "game_id". The "info" field must be set to one
of the following:

AUTO_MUCK_NEVER  0x00
AUTO_MUCK_WIN    0x01
AUTO_MUCK_LOSE   0x02
AUTO_MUCK_ALWAYS AUTO_MUCK_WIN + AUTO_MUCK_LOSE

When "info" is set to AUTO_MUCK_NEVER, the server will always send
a PacketPokerMuckRequest including the serial of the player for
this "game_id" when mucking is an option. If "info" is set to
AUTO_MUCK_WIN the server will
not include the serial of the player in the PacketPokerMuckRequest packet
for this "game_id" if the player wins but is not forced to
how its cards (i.e. when the opponent folded to him).
If "info" is set to AUTO_MUCK_LOSE the server will not include the serial
of the player in the PacketPokerMuckRequest packet for this "game_id"
when the player loses the hand but is not forced to show his cards.
AUTO_MUCK_ALWAYS is the equivalent of requesting AUTO_MUCK_LOSE and
AUTO_MUCK_WIN at the same time and is the default.

Direction: server <= client
game_id: integer uniquely identifying a game.
info: bitfield indicating what muck situations are of interest.
    """

    info = PacketPokerId.info + (
        ('auto_muck', 0xFF, 'B'),
        )

Packet.infoDeclare(globals(), PacketPokerAutoMuck, Packet, "POKER_AUTO_MUCK", 129) # 129 # 0x81
########################################

class PacketPokerMuckAccept(PacketPokerId):
    """
    """

Packet.infoDeclare(globals(), PacketPokerMuckAccept, Packet, "POKER_MUCK_ACCEPT", 130) # 130 # 0x82
########################################

class PacketPokerMuckDeny(PacketPokerId):
    """
    """
    
Packet.infoDeclare(globals(), PacketPokerMuckDeny, Packet, "POKER_MUCK_DENY", 131) # 131 # 0x83
########################################

class PacketPokerMoneyTransfert(PacketSerial):
    """
    """
    
    info = PacketSerial.info + (
        ('url', 'UNKNOWN', 's'),
        ('name', 'UNKNOWN', 's'),
        ('application_data', '', 's'),
        ('bserial', 0, 'I'),
        ('value', 0, 'I'),
        )

# class is not publicly available, but used as a base class
#Packet.infoDeclare(globals(), , Packet, "", ) #  #
########################################

class PacketPokerCashIn(PacketPokerMoneyTransfert):
    """\
Semantics: add "value" cents of currency "url" to the
"serial" player account using the "name"/"bserial" note.

Context: If the CASH_IN is successfull, PacketAck is returned.
Otherwise PacketError is returned with the "message" field set
to a human readable error explanation. The poker server must
be able to check the validity of the note provided
by accessing the currency server at "url".

The url, bserial, name, value fields content are filled from
the result of a request to a currency web service. For instance:

http://localhost/poker-web/currency_one.php?command=get_note&value=100&autocommit=yes

will return the following content

http://localhost/poker-web/currency_one.php     22      cfae906e9d7d6f6321b04d659059f4d6f8b86a34      100

that can be used to build a packet by setting:

url = http://localhost/poker-web/currency_one.php
bserial = 22
name = cfae906e9d7d6f6321b04d659059f4d6f8b86a34
value = 100

When the poker server honors the PacketPokerCashIn packet, it will
contact the currency server to change the note. It means the note sent
will become invalid and be replaced by a new one, known only to the
poker server.

Direction: server <= client

value: integer value of the note in cent
currency: url string of the currency server
bserial: integer value of the serial of the note
name: string cryptographic name of the note
note: tuple of (url, bserial, name, value) that overrides the parameters
      of the same name
serial: integer uniquely identifying a player.
"""
    DUPLICATE_CURRENCIES = 1
    REFUSED = 2
    SAFE = 3
    UNKNOWN = 4
    RETRY = 5

Packet.infoDeclare(globals(), PacketPokerCashIn, Packet, "POKER_CASH_IN", 132) # 132 # 0x84
########################################

class PacketPokerCashOut(PacketPokerMoneyTransfert):
    """
    """
    
    SAFE = 1
    BREAK_NOTE = 2
    EMPTY = 3

Packet.infoDeclare(globals(), PacketPokerCashOut, Packet, "POKER_CASH_OUT", 133) # 133 # 0x85
########################################

class PacketPokerCashOutCommit(Packet):

    info = Packet.info + (
        ('transaction_id', '', 's'), 
        )

    INVALID_TRANSACTION = 1

Packet.infoDeclare(globals(), PacketPokerCashOutCommit, Packet, "POKER_CASH_OUT_COMMIT", 134) # 134 # 0x86
########################################

class PacketPokerCashQuery(Packet):

    info = Packet.info + (
        ('application_data', '', 's'),
        )
    
    DOES_NOT_EXIST = 1

Packet.infoDeclare(globals(), PacketPokerCashQuery, Packet, "POKER_CASH_QUERY", 135) # 135 # 0x87
########################################

class PacketPokerRake(PacketInt):

    info = PacketInt.info + (
        ('game_id', 0, 'I'),
        )

Packet.infoDeclare(globals(), PacketPokerRake, Packet, "POKER_RAKE", 136) # 136 # 0x88
########################################

class PacketPokerTourneyRank(PacketPokerId):
    """\
Semantics: a PACKET_POKER_TOURNEY_RANK sent to the player who leaves the tournament

Direction: server  => client

serial: serial of the tourney

rank: the rank.

players: the number of players in this tourney

money: the money won
"""

    info = PacketPokerId.info + ( 
        ('players', 0, 'I'),
        ('money', 0, 'I'),
        ('rank', sys.maxint, 'I'),
        )

Packet.infoDeclare(globals(), PacketPokerTourneyRank, Packet, "POKER_TOURNEY_RANK", 137) # 137 # 0x89
########################################

class PacketPokerPlayerImage(PacketSerial):
    """
    """

    info = PacketSerial.info + (
        ('image', '', 's'),
        ('image_type', 'image/png', 's'),
        )

Packet.infoDeclare(globals(), PacketPokerPlayerImage, Packet, "POKER_PLAYER_IMAGE", 138) # 138 # 0x8a
########################################

class PacketPokerGetPlayerImage(PacketSerial):
    """
    """
    
Packet.infoDeclare(globals(), PacketPokerGetPlayerImage, Packet, "POKER_GET_PLAYER_IMAGE", 139) # 139 # 0x8b
########################################

class PacketPokerHandReplay(PacketPokerId):
    """
    """

Packet.infoDeclare(globals(), PacketPokerHandReplay, Packet, "POKER_HAND_REPLAY", 140) # 140 # 0x8c
########################################

class PacketPokerGameMessage(PacketPokerMessage):
    """
    """
    
Packet.infoDeclare(globals(), PacketPokerGameMessage, Packet, "POKER_GAME_MESSAGE", 141) # 141 # 0x8d
########################################

class PacketPokerExplain(PacketInt):
    """\
Semantics: control the level of verbosity of the server
according to the "value" bit field as follows:

Context: If the server accepts the request, a PacketAck is
returned. Otherwise a PacketError is returned with
other_type set to PACKET_POKER_EXPLAIN.

Note: in order to produce the desired behaviour, the
PACKET_POKER_EXPLAIN must be sent before starting to
observe the action at a table (i.e. before sending PACKET_POKER_JOIN)
and before any PACKET_POKER_LOGIN is sent.

value == NONE
  The server assumes the client knows the poker rules, presumably
  by using poker-engine.

value == ALL
  The server assumes the client does not know poker and will
  explain every game event in great detail.

Direction: server <= client
"""
    NONE       = 0x0000
    REST       = 0x0001
    CHIPSTACKS = 0x0004
    ALL        = REST | CHIPSTACKS

Packet.infoDeclare(globals(), PacketPokerExplain, PacketInt, "POKER_EXPLAIN", 142) # 142 # 0x8e # %SEQ%
########################################

class PacketPokerStatsQuery(PacketString):
    """ """
    
    pass #pragma: no cover
    
Packet.infoDeclare(globals(), PacketPokerStatsQuery, PacketString, "POKER_STATS_QUERY", 143) # 143 # 0x8f # %SEQ%
########################################

class PacketPokerStats(Packet):
    """ """
    
    info = Packet.info + (
        ('players', 0, 'I'),
        ('hands', 0, 'I'),
        ('bytesin', 0, 'I'),
        ('bytesout', 0, 'I'),
        )

Packet.infoDeclare(globals(), PacketPokerStats, Packet, "POKER_STATS", 144) # 144 # 0x90 # %SEQ%

########################################

class PacketPokerBuyInLimits(Packet):
    """\
Semantics: the buy-in boundaries for "game_id" in the range
["min","max"]. An optimal buy-in is suggested in "best". A
player is considered broke unless he has at least "rebuy_min"
at the table.

Direction: server => client

Context: sent immediately after the PacketPokerTable packet.

min: minimum buy-in in cent.
max: minimum buy-in in cent.
best: optimal buy-in in cent.
rebuy_min: the minimum amount to play a hand.
game_id: integer uniquely identifying a game.
    """
    
    info = Packet.info + (
        ('game_id', 0, 'I'),
        ('min', 0, 'I'),
        ('max', 0, 'I'),
        ('best', 0, 'I'),
        ('rebuy_min', 0, 'I'),
        )

Packet.infoDeclare(globals(), PacketPokerBuyInLimits, Packet, "POKER_BUY_IN_LIMITS", 145) # 145 # 0x91 # %SEQ%

########################################

class PacketPokerMonitor(Packet):
    """ """
    
    pass #pragma: no cover

Packet.infoDeclare(globals(), PacketPokerMonitor, Packet, "POKER_MONITOR", 146) # 146 # 0x92 # %SEQ%

########################################

class PacketPokerMonitorEvent(Packet):
    """ """
    ####
    # A hand is finished and has been archived in the hands table.
    # param1 = index in the hands table
    # param2 = 0 if cash game, 1 if tournament
    # 
    #
    HAND = 1

    ####
    # A tournament is complete and prizes were distributed.
    # param1 = tourney serial in the tourneys table
    #
    TOURNEY = 2

    ####
    # A player buys in at a cash game table.
    # param1 = user serial
    # param2 = table serial
    # param3 = buy in amount
    #
    BUY_IN = 3

    ####
    # A player was granted money by auto refill.
    # param1 = user serial
    # param2 = currency serial
    # param3 = total amount for this currency
    #
    REFILL = 4

    ###
    # A player won a prize at the end of a tournament.
    # param1 = user serial
    # param2 = currency serial
    # param3 = prize amount
    #
    PRIZE = 5

    ####
    # A player registered in a tournament.
    # param1 = user serial
    # param2 = currency serial
    # param3 = registration fees
    #
    REGISTER = 6

    ####
    # A player unregistered from a tournament.
    # param1 = user serial
    # param2 = currency serial
    # param3 = registration fees
    # 
    UNREGISTER = 7

    ####
    # A player left a poker table.
    # param1 = user serial
    # param2 = table serial
    #
    LEAVE = 8

    ####
    # A player got a seat at a poker table.
    # param1 = user serial
    # param2 = table serial
    #
    SEAT = 9

    ####
    # A tournament has started.
    # param1 = tourney serial in the tourneys table
    #
    TOURNEY_START       = 10
    
    info = Packet.info + (
        ('event', 0, 'I'),
        ('param1', 0, 'I'),
        ('param2', 0, 'I'),
        ('param3', 0, 'I')
        )

Packet.infoDeclare(globals(), PacketPokerMonitorEvent, Packet, "POKER_MONITOR_EVENT", 147) # 147 # 0x93 # %SEQ%

########################################

class PacketPokerGetTourneyManager(Packet):
    """
Semantics: Get tournement manager packet for tourney_serial

Direction: server <= client

If the tourney_serial is not found occurs, the server will send back

  PacketError(other_type = PACKET_POKER_GET_TOURNEY_MANAGER)

with the "code" field name set as follows:

DOES_NOT_EXIST : the "tourney_serial" field does not match any existing
                 tournaments.
"""
    info = Packet.info + (
        ('tourney_serial', 0, 'I'),
        )

    DOES_NOT_EXIST = 1

Packet.infoDeclare(globals(), PacketPokerGetTourneyManager, Packet, "POKER_GET_TOURNEY_MANAGER", 148) # 148 # 0x94 # %SEQ%

########################################

class PacketPokerTourneyManager(Packet):
    """ """
    
Packet.infoDeclare(globals(), PacketPokerTourneyManager, Packet, "POKER_TOURNEY_MANAGER", 149) # 149 # 0x95 # %SEQ%

########################################

class PacketPokerGetPlayerPlaces(Packet):
    """ """
    
    info = Packet.info + (
        ('serial', 0, 'I'),
        ('name', '', 's'),
        )

Packet.infoDeclare(globals(), PacketPokerGetPlayerPlaces, Packet, "POKER_GET_PLAYER_PLACES", 151) # 151 # 0x97 # %SEQ%

########################################

class PacketPokerPlayerPlaces(Packet):
    """ """
    
    info = Packet.info + (
        ('serial', 0, 'I'),
        ('tables', [], 'Il'),
        ('tourneys', [], 'Il'),
        )

Packet.infoDeclare(globals(), PacketPokerPlayerPlaces, Packet, "POKER_PLAYER_PLACES", 152) # 152 # 0x98 # %SEQ%

########################################

class PacketPokerSetLocale(PacketPokerId):
    """\

Semantics: the player "serial" is required to set the "locale" string,
which must be a locale supported by the server.  If the locale is
supported by the server, it will be made the locale used for strings sent
by PokerExplain packets.

Direction: server  <= client

Context: If the locale is supported by the server, a PacketAck is
returned, and future PokerExplain strings will be localized to the
requested language.  Otherwise a PacketError is returned with other_type
set to PACKET_POKER_SET_LOCALE.

locale: string representing a valid locale supported by the server configuration (e.g.,  "fr_FR" or "fr")
serial: integer uniquely identifying a player.
"""
# locale: string representing fully qualified locale and encoding, such as "fr_FR.UTF-8"

    info = PacketPokerId.info + ( ('locale', 'en_US', 's'), )

Packet.infoDeclare(globals(), PacketPokerSetLocale, PacketSerial, "POKER_SET_LOCALE", 153) # 153 # 0x99 # %SEQ%

########################################
class PacketPokerTableTourneyBreakBegin(Packet):
    """\

Semantics: Players at table "game_id" will receive this packet when a
tournament break offically begins.

Direction: server  => client

Context: 

game_id: integer uniquely identifying a game.
resume_time: time that the tourney will resume, in seconds since 1970-01-01 00:00:00 UTC.
"""
    info = Packet.info + (
        ('game_id', 0, 'I'),
        ('resume_time', 0, 'I'),
        )

Packet.infoDeclare(globals(), PacketPokerTableTourneyBreakBegin, Packet, "POKER_TABLE_TOURNEY_BREAK_BEGIN", 154) # 154 # 0x9a # %SEQ%

# infoDeclare would clobber our custom __str__ if we set it in the lass, so replace it here.
def PacketPokerTableTourneyBreakBegin__str__(self):
        return Packet.__str__(self) + "game_id = %d, resume_time = %s" % ( self.game_id,strftime("%Y/%m/%d %H:%M", gmtime(self.resume_time)))
PacketPokerTableTourneyBreakBegin.__str__ = PacketPokerTableTourneyBreakBegin__str__

########################################
class PacketPokerTableTourneyBreakDone(Packet):
    """\

Semantics: Players at table "game_id" will receive this packet when a
tournament break offically ends.

Direction: server  => client

Context: 

game_id: integer uniquely identifying a game.
"""
    info = Packet.info + (
        ('game_id', 0, 'I'),
        )


Packet.infoDeclare(globals(), PacketPokerTableTourneyBreakDone, Packet, "POKER_TABLE_TOURNEY_BREAK_DONE", 155) # 155 # 0x9b # %SEQ%

########################################

class PacketPokerTourneyStart(PacketSerial):
    """\

Semantics: If sent from the server: The "tourney_serial" tournament started and
the player is seated at table "table_serial". If sent from a client with appropriate
permissions, the tourney will be started before it's start_time.

Direction: server <=> client

Context: this packet is sent to the client when it is logged in. The 
player seated at the table "table_serial" is implicitly the logged in player.

serial: integer uniquely identifying a player. 
tourney_serial: integer uniquely identifying a tournament.
table_serial: integer uniquely identifying a game.
"""
    DOES_NOT_EXIST = 1
    WRONG_STATE = 2
    NOT_BAILOR = 3
    
    info = PacketSerial.info + (
            ('tourney_serial', 0, 'I'),
            ('table_serial', 0, 'I')
            )

Packet.infoDeclare(globals(), PacketPokerTourneyStart, Packet, "POKER_TOURNEY_START", 156) # 0x9c # %SEQ%

########################################
class PacketPokerGetTourneyPlayerStats(PacketSerial):
    """\
    
Semantics: if the player "serial" is participating in the tourney
           "tourney_serial", he can ask for information about his
           current performance (i.e. his rank) in the tourney and
           compare it to the chips leader and the average chips 
           amount.

Direction: server  <=  client

Context: the packet can be sent by the player as long as the tourney
         is loaded in memory on the server. he will receive an error
         if the tourney is not existing (DOES_NOT_EXIST) or he is or
         was not participating in the tourney (NOT_PARTICIPATING).

serial: integer uniquely identifying a player.
tourney_serial: integer uniquely indentifying a tourney.
"""
    info = PacketSerial.info + (
            ('tourney_serial',0,'I'),
            )
    
    DOES_NOT_EXIST = 1
    NOT_PARTICIPATING = 2
    
Packet.infoDeclare(globals(), PacketPokerGetTourneyPlayerStats, Packet, "POKER_GET_TOURNEY_PLAYER_STATS", 157) # 0x9d # %SEQ%

########################################
class PacketPokerTourneyPlayerStats(PacketSerial):
    """\
Semantics: contains personalized information for user "serial"
           for tourney "tourney_serial" such as his rank, the 
           current chips leader, and so forth.

Direction: server  =>  client

Context: the packet is sent as a response to PacketPokerGetTourneyPlayerStats

serial: integer uniquely identifying a player.
tourney_serial: integer uniquely indentifying a tourney.
rank: integer the current rank of the player
players_active: integer the number of players who are 
                still participating in the tourney
chips_avg: the average amount of chips an active player has
chips_max: the amount of chips the highest ranked player has
player_chips_max_serial: the serial of the currently leading player
player_chips_max_name: the name of the currently leading player
"""
    info = PacketSerial.info + (
            ('tourney_serial',0,'I'),
            ('rank',0,'H'),
            ('players_active',0,'H'),
            ('chips_avg',0,'Q'),
            ('chips_max',0,'Q'),
            ('player_chips_max_serial',0,'I'),
            ('player_chips_max_name','noname','s'),
            )
    
Packet.infoDeclare(globals(), PacketPokerTourneyPlayerStats, Packet, "POKER_TOURNEY_PLAYER_STATS", 158) # 0x9e # %SEQ%

########################################
class PacketPokerStateInformation(PacketPokerId):
    """\
Semantics: This message is sent to a client whenever the server
           has an inconsistent or otherwise not useful state of the player's
           session object. This packet should help the user to decide how to
           reinstate a correct connection by e.g. re-issuing a PacketPokerTableJoin
           or a PacketLogin packet
           
Direction: server  =>  client

Context: Since this packet is sent on the server's behalf, usually without the 
         client's direct interaction. It is difficult to define a determined context 
         for it. It is however possible to deduce if the packet is referring to a 
         determined game or not, by looking at the "game_id" field.
         The following error codes are currently used:
         - REMOTE_CONNECTION_LOST: The server is closing the connection to another
                                   remote server, because the session on the server the
                                   client is connected to is expired. 
         - REMOTE_TABLE_EPHEMERAL: Denotes the fact that after the current request the
                                   client's session will be destroyed again. This usually
                                   happens if the server never received a PacketPokerTable 
                                   packet on this connection --> send a PacketPokerTableJoin
                                   packet.
         - SHUTTING_DOWN:          The table at game_id will be gone after the current hand.
                                   This message is sent to the clients on behalf of the server
                                   when the server is shutting down.
          
serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game.
message: string representing the error.
code: integer representing the error.
"""

    REMOTE_CONNECTION_LOST = 1
    REMOTE_TABLE_EPHEMERAL = 2
    LOCAL_TABLE_EPHEMERAL = 3
    SHUTTING_DOWN = 4
    
    
    info = PacketPokerId.info + (
        ('code',0,'I'),
        ('message','no message','s')
        )

Packet.infoDeclare(globals(), PacketPokerStateInformation, Packet, "POKER_STATE_INFORMATION", 160) # 160 # 0xa0 # %SEQ%

########################################
class PacketPokerPlayerStats(PacketPokerId):
    """\

Semantics: the "rank" and "percentile" of the player "serial"
for the "currency_serial" currency. The player with the largest
amount of "currency_serial" money has "rank" 1. The "rank" is therefore
in the range [1..n] where n is the total number of players registered
on the poker server. The players are divided in G groups and the "percentile" is
the number of the player group. For instance, if the players are divided in 4 groups
the top 25% players will be in "percentile" 0, the next
25% will be in "percentile" 1 and the last
25% will be in "percentile" 3. The player with "rank" is always in
"percentile" 0 and the player with least chips in the "currency_serial"
money is always in the last "percentile".

Direction: server  => client

Context: 

serial: integer uniquely identifying a player.
game_id: integer uniquely identifying a game. (optional)
currency_serial: int currency id
rank: rank of the player 
percentile: percentile of the player
"""
    NOT_FOUND = 1

    info = PacketPokerId.info + (
        ('currency_serial', 0, 'I'),
        ('rank', 0, 'I'),
        ('percentile', 0, 'I')
        )

Packet.infoDeclare(globals(), PacketPokerPlayerStats, Packet, "POKER_PLAYER_STATS", 161) # 161 # 0xa1 # %SEQ%

########################################
class PacketPokerTablePicker(PacketPokerId):
    """\

Semantics: The player "serial" wishes to join a table that matches the
           criteria sent.  Empty or non existing entries in criteria means
           "match any".  The table that matches the given criteria, and
           has the most players already seated (but with a seat available
           for the requesting player) will be returned.  An error is
           returned if such a table cannot be found.  If multiple tables
           are equally appropriate, the one with the smallest serial is
           returned.

           Note that the player has to be logged in order to pick a table,
           the "serial" field is mandatory.

           An additional criterion that is *not* sent by the user (but
           rather inferred by the server) is as follows: cash game tables
           whose minimum buy-in is less than the amount of money available
           to the player in a given currency are eliminated from
           consideration.

           If a table matching the criteria is available, it will be as if
           the client had sent the following sequence of packets (plus
           performed the pseudo-code logic below on client side):

               Send: PacketPokerTableJoin()
               Send: PacketPokerSeat()
               if auto_blind_ante: # in original packet
                    Send: PacketPokerAutoBlindAnte()
               Receive: PacketPokerBuyInLimits() [ returning "best", "min" ]
               if player.money_available < best:
                    Send: PacketPokerBuyIn(amount = min)
               else:
                    Send: PacketPokerBuyIn(amount = best)
               Send: PacketPokerSit()

           In the case of failure, an error packet as follows will be sent
           to the client:
             PacketPokerError(code      = PacketPokerTableJoin.GENERAL_FAILURE,
                              message   = <some string of non-zero length, for use
                                          in displaying to the user>,
                             other_type = PACKET_POKER_TABLE_PICKER,
                             serial     = <player's serial id>,
                             game_id    = <if failure occured before table matching criteria was identified: 0
                                           else: game.id for table where join was attempted>)

           In this case of success, the client can expect to receive all
           the packets that it would expect to receive in response to any
           of the packets listed in "Send" above.  These include:
                  PacketPokerTable()        # info about the table joined
                  PacketPokerBuyInLimits()  # still sent despite mention in pseudo-code above
                  PacketPokerPlayerArrive() # for client.serial
                  PacketPokerPlayerChips()  # for client.serial
                  if auto_blind_ante:
                    PacketPokerAutoBlindAnte()
                  PacketPokerSit()          # for client.serial
                  PacketPokerSeats()
              
           Note even if a valid PacketPokerTable() is received, it's
           possible, although unlikely, that the intervening operations --
           PacketPokerSeat(), PacketPokerBuyIn() and PacketPokerSit() --
           might fail.  If one of them fails, the client should expect to
           receive the normal errors it would receive if such an operation
           failed.  Clients are advised, upon receiving a valid
           PacketPokerTable() in response, to use the same handling
           routines that it uses for PacketPokerSeat(), PacketPokerBuyIn()
           and PacketPokerSit() to keep parity with the operations the
           server is performing on the client's behalf.

Direction: server <=  client

Context:

serial: integer uniquely identifying a player.
currency_serial: int currency id (criteria for search)
variant: base name of the variant sought.
betting_structure: base name of the betting structure.
auto_blind_ante: boolean, if True server will act as if
                PacketPokerAutoBlindAnte() were also sent by client.
                Defaults to False.
"""
    info = PacketPokerId.info + (
        ('currency_serial', 0, 'I'),
        ('min_players', 0, 'I'),
        ('variant', '', 's'),
        ('betting_structure', '', 's'),
        ('auto_blind_ante', False, 'bool'),
        )

Packet.infoDeclare(globals(), PacketPokerTablePicker, Packet, "POKER_TABLE_PICKER", 165) # 165 # 0xa5 # %SEQ%

########################################
class PacketPokerCreateTourney(PacketSerial):
    """\

Semantics: The authorized player represented by "serial",
           seeks to create a new sit-n-go tournament for the players in
           the "players" list of serials. Each player in the list will
           be registered for the new tournament.

           The fields "name", "description_short", "description_long", "variant",
           "betting_structure", "seats_per_game", "player_timeout", "currency_serial"
           and "buy_in" have the same semantics as described in the database schema.

           Upon success, the response will be PacketAck() for the new sit-n-go tournament.
           If the request is issued by a user that is not authentified, the response will be:
                 PacketAuthRequest()
           If at least one user cannot be registered, the response will be:
                 PacketPokerError(
                   other_type = PACKET_POKER_CREATE_TOURNEY,
                   code       = REGISTRATION_FAILED 
                   serial     = the serial of the tournament for which registration failed

                   Note: the list of players for which registration has failed is included
                   in the message. An error message will be sent to each players for which
                   registration failed, if they have an active session.

Direction: server <=  client

Context:

serial:            integer uniquely identifying the administrative-level player.
name:              name for tournament
description_short: Short description of tournament
description_long:  Long description of tournament
variant:           base name of the variant for the new sit-n-go
betting_structure: base name of the betting structure that must
                   match a poker.<betting_structure>.xml file containing
                   a full description of the betting structure.
seats_per_game:     Maximum number of seats for each table in this tournament.
player_timeout:    the number of seconds after which a player in position is forced to
                   play (by folding).
currency_serial:   int currency id
buy_in:            Amount, in currency_serial, for buying into this tournament.
players_quota      Quota of the tournament. If smaller than len(players), len(players) 
                   is used (i.e. the tourney starts immediately).
players:           Serials of the players participating in the tournament.
"""
    REGISTRATION_FAILED = 1
    
    info = PacketSerial.info + (
        ('name', 'noname', 's'),
        ('description_short', 'nodescription_short', 's'),
        ('description_long', 'nodescription_long', 's'),
        ('variant', 'holdem', 's'),
        ('betting_structure', 'level-001', 's'),
        ('seats_per_game', 9, 'I'),
        ('player_timeout', 60, 'I'),
        ('currency_serial', 0, 'I'),
        ('buy_in', 0, 'I'),
        ('bailor_serial',0,'I'),
        ('players_quota',0,'I'),
        ('players', [], 'Il')
        )

Packet.infoDeclare(globals(), PacketPokerCreateTourney, Packet, "POKER_CREATE_TOURNEY", 166) # 166 # 0xa6 # %SEQ%

########################################
class PacketPokerLongPoll(PacketPokerId):
    """ """
    
    info = PacketPokerId.info

Packet.infoDeclare(globals(), PacketPokerLongPoll, Packet, "POKER_LONG_POLL", 167) # 167 # 0xa7 # %SEQ%

########################################
class PacketPokerLongPollReturn(Packet):
    """ """
    
    info = Packet.info

Packet.infoDeclare(globals(), PacketPokerLongPollReturn, Packet, "POKER_LONG_POLL_RETURN", 168) # 168 # 0xa8 # %SEQ%

########################################

    
_TYPES = range(50,169)

# Interpreted by emacs
# Local Variables:
# compile-command: "perl -pi -e 'if(/%SEQ%/) { $s = 49 if(!defined($s)); $s++; $h = sprintf(q/0x%x/, $s); s/\\d+[ \\w#]+#/$s # $h #/; }' pokerpackets.py"
# End:

#
# only export things starting with Packet or PACKET_
import re
__all__ = [n for n in locals().keys() if re.match('Packet|PACKET_',n)]

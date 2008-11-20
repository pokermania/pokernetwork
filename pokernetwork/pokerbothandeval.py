#
# Copyright (C) 2007, 2008 Loic Dachary <loic@dachary.org>
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
from pokereval import PokerEval
class PokerHandEval:
    def __init__(self):
        self.hand_groups = {
            "A":["AA", "AKs", "KK"],
            "B":["AK", "QQ"],
            "C":["JJ", "TT"],
            "D":["AQs", "AQ", "AJs", "99", "88"],
            "E":["AJ","ATs","KQs", "77","66","55"],
            "F":["AT","KQ","KJs","QJs","44","33","22"],
            "G":["A9s","A8s","A7s","A6s","A5s","A4s","A3s","A2s","KTs","QTs","JTs","J9s","T9s","98s"],
            "H":["KJ","KT","QJ","J8s","T8s","87s","76s"]
        }
        self.hand_values = {"A":13,"K":12,"Q":11,"J":10, "T":9,"9":8,"8":7,"7":6,"6":5,"5":4,"4":3,"3":2,"2":1}
        self.odds_map = {
            "flop":{1:0.045,2:0.088,3:0.13,4:0.172,5:0.212,6:0.252,7:0.29,8:0.327,9:0.364,10:0.399,11:0.433,12:0.467,13:0.499,14:0.53,15:0.561,16:0.59,17:0.618},
            "turn":{1:0.023,2:0.045,3:0.68,4:0.091,5:0.114,6:0.136,7:0.159,8:0.182,9:0.205,10:0.227,11:0.25,12:0.273,13:0.295,14:0.318,15:0.341,16:0.364,17:0.386}
        }
        self.eval = PokerEval()
    def prepareHand(self, hand):
        h = hand.split(" ")
        if self.hand_values[h[1][0]] > self.hand_values[h[0][0]]:
            self.hand = "%s%s" % (h[1][0],h[0][0])
        else:
            self.hand = "%s%s" % (h[0][0],h[1][0])
        if h[0][1] == h[1][1]:
            self.hand += "s"
    def getHandGroup(self):
        for group in self.hand_groups:
            if self.hand in self.hand_groups[group]:
                return group
        return False
    def getHandValue(self, game, serial):
        hand = game.getHandAsString(serial)
        board = game.getBoardAsString()
        board_list = board.split(" ")
        if len(board_list) < 5:
            for i in range(len(board_list), 5):
                board_list.append("__")
        hand_list = hand.split(" ")
        cards = hand_list + board_list
        return self.eval.best_hand("hi", self.eval.string2card(cards), [] )
    def parseHistory(self, hist):
        self.round_action = {}
        self.action2serials = {
            "call":[],
            "raise":[],
            "fold":[]
        }
        self.serial2action = {}
        ret = ""
        for event in hist:
            type = event[0]
            if type in ["fold","check","call","raise"]:
                if len(event) == 3:
                    (action, serial, amount) = event
                else:
                    (action,serial) = event
                    amount = False
                ret = "action: %s, serial:%d" % (action, serial)
                if amount:
                    ret += ", amount = %d" % amount
                    self.round_action[serial] = [action, amount]
                else:
                    self.round_action[serial] = [action]
                self.serial2action[serial] = action
                if action in self.action2serials.keys():
                    if not serial in self.action2serials[action]:
                        self.action2serials[action].append(serial)
    def getPosition(self, game, serial):
        me = game.serial2player[serial]
        players = game.serialsAllSorted()
        for player in players:
            user = game.serial2player[player]
        user_positions = {}
        player_seats = {}
        i=1
        for p in game.serialsAllSorted():
            user = game.serial2player[p]
            player_seats[user.seat] = p
        max_seat = len(player_seats)
        early = max_seat / 3
        middle = early * 2
        self.my_seat = me.seat
        self.serial2position = {}
        self.position2serials = {
            "early":[],
            "middle":[],
            "late":[]
        }
        for p in player_seats.keys():
            player_serial = player_seats[p]
            if i <= early:
                position = "early"
            elif i >= (early + 1) and i <= middle:
                position = "middle"
            else:
                position = "late"
            if not player_serial in self.serial2position.keys():
                self.serial2position[player_serial] = position
            if not player_serial in self.position2serials[position]:
                self.position2serials[position].append(player_serial)
            if p == self.my_seat:
                self.position = position
            i += 1
class PreFlopHandEval(PokerHandEval):
    def hasPreflopRaise(self, game):
        self.parseHistory(game.historyGet())
        if len(self.action2serials["raise"]) != 0:
            return True
        return False
    def evalHand(self, hand, game, serial):
        self.prepareHand(hand)
        self.hand_group = self.getHandGroup()
        action = "fold"
        s = game.serialsAllSorted()
        big_blind = game.serial2player[s[1]]
        small_blind = game.serial2player[s[0]]
        me = game.serial2player[serial]
        self.getPosition(game, serial)
        raised = self.hasPreflopRaise(game)
        if me.name in [big_blind.name,small_blind.name]:
            in_blinds = True
        else:
            in_blinds = False
        if self.hand_group != False:
            if raised != False:
                user  = game.serial2player[self.action2serials["raise"][0]]
                self.raised_from = self.serial2position[self.action2serials["raise"][0]]
                if self.position == "early":
                    if in_blinds:
                        if self.raised_from == "early":
                            if self.hand_group == "A":
                                action = "raise"
                            elif self.hand_group in ["B","C","D"]:
                                action = "call"
                            else:
                                action = "fold"
                        elif self.raised_from == "middle":
                            if self.hand_group in ["A","B","C"]:
                                action = "raise"
                            elif self.hand_group in ["D","E"]:
                                action = "call"
                            else:
                                action = "fold"
                        else:
                            if self.hand_group in ["A","B","C","D"]:
                                action = "raise"
                            elif self.hand_group in ["E","F"]:
                                action = "call"
                            else:
                                action = "fold"
                    else:
                        if self.hand_group == "A":
                            action = "raise"
                        elif self.hand_group in ["B","C"]:
                            action = "call"
                        else:
                            action = "fold"
                elif self.position == "middle":
                    if self.hand_group in ["A","B"]:
                        action = "raise"
                    elif self.hand_group == "C":
                        action = "call"
                    else:
                        action = "fold"
                else:
                    if self.hand_group in ["A", "B"]:
                        action = "raise"
                    elif self.hand_group in ["C","D"]:
                        action = "call"
                    else:
                        action = "fold"
            else:
                if self.position == "early":
                    if self.hand_group in ["A","B","C","D"]:
                        action = "raise"
                    else:
                        action = "fold"
                elif self.position == "middle":
                    if self.hand_group in ["A","B","C","D", "E"]:
                        action = "raise"
                    elif self.hand_group in ["F", "G"]:
                        action = "call"
                    else:
                        action = "fold"
                else:
                    if self.hand_group in ["A","B","C","D", "E", "F"]:
                        action = "raise"
                    elif self.hand_group in ["G","H"]:
                        action = "call"
        else:
            actions = game.possibleActions(serial)
            if not "fold" in actions:
                action = "check"
            else:
                action = "fold"
        return action
class PostFlopHandEval(PokerHandEval):
    def evalHand(self, ev, game, serial):
        action = "fold"
        hand = game.getHandAsString(serial)
        board = game.getBoardAsString()
        hand_value = self.getHandValue(game, serial)
        me = game.serial2player[serial]
        if hand_value[0] == "NoPair":
            if not game.betsNull() and game.state in ["flop","third","turn","fourth"]:
                pot = game.getPotAmount()
                bet = game.getUncalled()
                draw = EvalDraws(self.hand_values, hand, board)
                has_draw = draw.lookForDraws()
                if has_draw != False:
                    odds_map = False
                    if game.state in ["flop", "third"]:
                        odds_map = self.odds_map["flop"]
                    elif game.state in ["turn", "fourth"]:
                        odds_map = self.odds_map["turn"]
                    if odds_map != False:
                        outs_map = {"GutShotStraight":4,"OpenEndedStraight":8,"FlushDraw":9}
                        outs_map["GutShotStraightFlush"] = outs_map["FlushDraw"] + (outs_map["GutShotStraight"] - 1)
                        outs_map["OpenEndedStraightFlush"] = outs_map["FlushDraw"] + (outs_map["OpenEndedStraight"] - 2)
                        odds_win = odds_map[outs_map[has_draw]]
                        my_ev = (pot * odds_win) - (bet * (1 - odds_win))
                        if my_ev >= 0:
                            action = "call"
                        else:
                            action = "fold"
                else:
                    action = "check"
            else:
                action = "check"
        elif hand_value[0] == "OnePair":
            board_list = []
            hand_list = hand.split(" ")
            draw = EvalDraws(self.hand_values, hand, board)
            has_draw = draw.lookForDraws()
            for card in board.split(" "):
                if self.hand_values[card[0]] > self.hand_values[hand_list[0][0]]:
                    if has_draw != False:
                        action = "call"
                    else:
                        action = "check"
        elif hand_value[0] in ["TwoPair","Trips","Straight","Flush","Flhouse","Quads","StFlush"]:
            action = "raise"
        return action
class EvalDraws:
    def __init__(self, had_values, hand, board):
        self.eval = PokerEval()
        self.hand_values = {"A":13,"K":12,"Q":11,"J":10, "T":9,"9":8,"8":7,"7":6,"6":5,"5":4,"4":3,"3":2,"2":1}
        self.hand = hand
        self.board = board
    def convertHandValue(self, cards):
        deck = []
        for card in cards:
            deck.append(self.hand_values[card[0]])
        return sorted(deck)
    def lookForDraws(self):
        h = self.hand.split(" ")
        b = self.board.split(" ")
        cards = h + b
        has_flush = self.lookForFlushDraw(cards)
        if has_flush != False:
            return has_flush
        has_straight = self.lookForStraightDraw(cards, False)
        if has_straight != False:
            return has_straight
        return False
    def lookForFlushDraw(self, cards):
        suits = {"s":0,"c":0,"h":0,"d":0}
        for card in cards:
            if card != "__":
                suits[card[1]] += 1
        for suit in suits:
            if suits[suit] > 3:
                has_straight = self.lookForStraightDraw(cards, True)
                if has_straight != False:
                    return "%s%s" %(has_straight, "Flush")
                return "FlushDraw"
        return False
    def lookForStraightDraw(self, cards, flush = False):
        if flush != False:
            deck = sorted(self.eval.string2card(cards))
        else:
            deck = self.convertHandValue(cards)
        for k,v in enumerate(deck):
            max_len = 3
            if (k + max_len) < len(deck) :
                my_range = range(v, (v + (max_len + 1)))
                if deck[k+max_len] == my_range[len(my_range) - 1]:
                    return "OpenEndedStraight"
                elif deck[k+max_len] == ((my_range[len(my_range) - 1] +1) or (my_range[len(my_range) - 1] - 1)):
                    return "GutShotStraight"
        return False
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
#  Loic Dachary <loic@gnu.org>
#
from os.path import exists

import pygame

from twisted.internet import reactor

from pokernetwork.pokerpackets import *
from pokerclient2d import pokeranimation2d
from pokerengine.pokerchips import PokerChips

from pokerui.pokerdisplay import PokerDisplay

import gtk
import gtk.glade

class PokerPlayer2D:
    def __init__(self, player, table):
        self.table = table
        self.player = player
        self.verbose = table.verbose
        self.seat = -1
        self.serial = player.serial
        self.best_cards = { 'hi': None, 'low': None }
        self.setSeat(player.seat)
        self.setOutfit(player.url, player.outfit)

    def message(self, string):
        print "[PokerPlayer2D " + str(self.table.game.id) + "/" + str(self.serial) + "] " + string

    def error(self, string):
        self.message("ERROR " + string)

    def setSeat(self, seat):
        glade = self.table.glade
        self.seat = seat
        self.name = glade.get_widget("name_seat%d" % seat)
        self.name.set_text(self.player.name)
        self.name.show()
        self.money = glade.get_widget("money_seat%d" % seat)
        self.money.show()
        self.bet = glade.get_widget("bet_seat%d" % seat)
        self.bet.hide()
        self.cards = map(lambda x: glade.get_widget("card%d_seat%d" % ( x, seat )), xrange(1,8))

    def setOutfit(self, url, outfit):
        color = gtk.gdk.color_parse(outfit)
        self.name.modify_fg(gtk.STATE_NORMAL, color)

    def updateChips(self, bet, money):
        if bet > 0:
            self.bet.set_text(PokerChips.tostring(bet))
            self.bet.show()
        else:
            self.bet.hide()
        self.money.set_text(PokerChips.tostring(money))

    def updateCards(self):
        game = self.table.game
        glade = self.table.glade
        player = game.getPlayer(self.serial)
        cards_numbers = player.hand.tolist(True)
        cards_names = game.eval.card2string(cards_numbers)
        if self.verbose > 2: self.message("updateCards " + str(cards_names))
        cards_count = len(cards_numbers)
        for card_index in xrange(len(self.table.cards_slots)):
            card_slot = self.table.cards_slots[card_index]
            if card_index >= cards_count:
                self.cards[card_slot].hide()
            else:
                if cards_numbers[card_index] == 255:
                    self.cards[card_slot].set_from_file(glade.relative_file("pixmaps/cards/small-back.jpg"))
                else:
                    self.cards[card_slot].set_from_file(glade.relative_file("pixmaps/cards/small-%s.jpg" % cards_names[card_index]))
                self.cards[card_slot].show()

    def hideCards(self):
        for card in self.cards:
            card.hide()

    def start(self):
        self.hideCards()
        self.best_cards = { 'hi': None, 'low': None }
        
    def render(self, packet):
        if self.verbose > 3: print "PokerPlayer2D::render: " + str(packet)

        if packet.type == PACKET_POKER_PLAYER_LEAVE:
            self.name.hide()
            self.money.hide()
            self.bet.hide()
            for card in self.cards:
                card.hide()
            self.table.deletePlayer(self.serial)
            self.seat = -1

        elif packet.type == PACKET_POKER_BEST_CARDS:
            side = packet.side and packet.side or "hi"
            self.best_cards[side] = packet
            self.updateCards()
            
        elif packet.type == PACKET_POKER_PLAYER_CHIPS:
            self.updateChips(packet.bet, packet.money)

        elif packet.type == PACKET_POKER_PLAYER_CARDS:
            self.updateCards()
            
        elif packet.type == PACKET_POKER_FOLD:
            for card in self.cards:
                card.hide()

class PokerTable2D:
    def __init__(self, table, display):
        self.display = display
        self.game = display.factory.getGame(table.id)
        self.glade = self.display.glade
        self.window = self.glade.get_widget("game_toplevel")
        self.serial2player = {}
        self.verbose = display.verbose
        self.resetCardsSlots()
        self.board = map(lambda x: self.glade.get_widget("board%d" % x), xrange(1,6))
        self.dealer_buttons = map(lambda x: self.glade.get_widget("dealer%d" % x), xrange(10))
        self.pots = map(lambda x: self.glade.get_widget("pot%d" % x), xrange(9))
        self.winners = map(lambda x: self.glade.get_widget("winner%d" % x), xrange(9))
        self.seats = map(lambda x: self.glade.get_widget("sit_seat%d" % x), xrange(10))
        if self.game.isTournament():
            for seat in self.seats:
                seat.hide()
        self.table_status = self.glade.get_widget("table_status").get_buffer()
        self.self_seated = False

    def message(self, string):
        print "[PokerTable2D " + str(self.game.id) + "] " + string

    def error(self, string):
        self.message("ERROR " + string)

    def reset(self):
        self.serial2player = {}
        fixed = self.glade.get_widget("game_fixed")
        for widget in fixed.get_children():
            if widget.get_name() != "switch":
                widget.hide()
        if not self.game.isTournament():
            for seat in self.seats:
                seat.show()
        self.glade.get_widget("quit").show()
        self.glade.get_widget("rebuy").show()
        self.glade.get_widget("raise_increase").show() # 1x1 button used for accelerators
        self.glade.get_widget("raise_decrease").show() # 1x1 button used for accelerators
        self.glade.get_widget("raise_increase_bb").show() # 1x1 button used for accelerators
        self.glade.get_widget("raise_decrease_bb").show() # 1x1 button used for accelerators
        self.glade.get_widget("raise_pot").show() # 1x1 button used for accelerators
        self.glade.get_widget("raise_half_pot").show() # 1x1 button used for accelerators
        self.updateTableStatus()
        self.glade.get_widget("table_status").show()
        
    def updateTableStatus(self):
        game = self.game
        if game.id != self.display.protocol.getCurrentGameId():
            return
        if game.isTournament():
            lines = [ game.name,
                      game.getVariantName(),
                      "Level %d" % game.getLevel(),
                      "Next level in %d %s" % game.delayToLevelUp() ]
        else:
            lines = [ game.name,
                      game.getVariantName() + " " + game.getBettingStructureName() ]
        if game.isRunning():
            lines.append("Playing hand #%d" % game.hand_serial)
        self.table_status.set_text("\n".join(lines))
    
    def resetCardsSlots(self):
        max_hand_size = self.game.getMaxHandSize()
        if self.verbose > 2: self.message("max hand size = %d" % max_hand_size)
        if max_hand_size == 2:
            self.cards_slots = ( 2, 4 )
        elif max_hand_size == 4:
            self.cards_slots = ( 0, 2, 4, 6 )
        else:
            self.cards_slots = range(max_hand_size)
        
    def deletePlayer(self, serial):
        del self.serial2player[serial]
        
    def deleteTable(self):
        self.display.deleteTable(self.game.id)

    def render(self, packet):
        if self.verbose > 3: self.message("render: " + str(packet))

        if packet.type == PACKET_POKER_TABLE_DESTROY:
            self.deleteTable()
            
        elif packet.type == PACKET_POKER_PLAYER_ARRIVE:
            self.serial2player[packet.serial] = PokerPlayer2D(packet, self)
            if packet.serial == self.display.protocol.getSerial():
                self.self_seated = True
                for seat in self.seats:
                    seat.hide()
            else:
                self.seats[packet.seat].hide()

        elif packet.type == PACKET_POKER_START:
            for (serial, player) in self.serial2player.iteritems():
                player.start()
            for winner in self.winners:
                winner.hide()
            self.updateTableStatus()

        elif packet.type == PACKET_POKER_CHIPS_POT_RESET:
            for pot in self.pots:
                pot.hide()

        elif packet.type == PACKET_POKER_BOARD_CARDS:
            board = self.game.eval.card2string(self.game.board.cards)
            board_length = len(board)
            for i in xrange(5):
                if i >= board_length:
                    self.board[i].hide()
                else:
                    self.board[i].set_from_file(self.glade.relative_file("pixmaps/cards/small-%s.jpg" % board[i]))
                    self.board[i].show()

        elif packet.type == PACKET_POKER_BET_LIMIT:
            self.bet_limit = packet

        elif packet.type == PACKET_POKER_HIGHEST_BET_INCREASE:
            self.display.updateRaiseRange(selected_amount = None)

        elif packet.type == PACKET_POKER_DEALER:
            self.dealer_buttons[packet.dealer].show()
            if packet.previous_dealer >= 0:
                self.dealer_buttons[packet.previous_dealer].hide()

        elif packet.type == PACKET_POKER_POT_CHIPS:
            pots = self.game.getPots()
            pot = self.pots[packet.index]
            pot.set_label(PokerChips.tostring(pots['pots'][packet.index][0]))
            pot.show()

        elif packet.type == PACKET_POKER_CHIPS_POT2PLAYER:
            if packet.reason != "win":
                return
            best_cards = self.serial2player[packet.serial].best_cards
            winner = self.winners[packet.pot]
            if self.game.hasLow() and self.game.hasHigh():
                if best_cards['hi'] and best_cards['low']:
                    label = "High: " + best_cards['hi'].hand + ", Low: " + best_cards['low'].hand
                elif best_cards['hi']:
                    label = "High: " + best_cards['hi'].hand
                elif best_cards['low']:
                    label = "Low: " + best_cards['low'].hand
                else:
                    label = None
                if label:
                    winner.set_label(label)
                    winner.show()
            elif self.game.hasHigh() and best_cards['hi']:
                winner.set_label(best_cards['hi'].hand)
                winner.show()
            elif self.game.hasLow() and best_cards['low']:
                winner.set_label(best_cards['low'].hand)
                winner.show()

        elif packet.type == PACKET_POKER_POSITION:
            for player in self.serial2player.values():
                playerInPosition = player.serial == packet.serial
                name = player.player.name
                if playerInPosition:
                    name = "<u>%s</u>" % name 
                player.name.set_use_markup(True)
                player.name.set_label(name)
                
        elif hasattr(packet, "serial") and self.serial2player.has_key(packet.serial):
            self.serial2player[packet.serial].render(packet)
            if packet.type == PACKET_POKER_PLAYER_LEAVE:
                serial = self.display.protocol.getSerial()
                if ( packet.serial == serial and
                     not self.game.isTournament() ):
                    for seat in self.seats:
                        seat.show()
                    for player in self.serial2player.values():
                        self.seats[player.seat].hide()
                elif serial in self.serial2player.keys():
                    self.seats[packet.seat].hide()
                else:
                    self.seats[packet.seat].show()

class PokerDisplay2D(PokerDisplay):
    def __init__(self, *args, **kwargs):
        PokerDisplay.__init__(self, *args, **kwargs)
        pygame.mixer.init()
        self.settings.notifyUpdates(self.settingsUpdated)
        self.settingsUpdated(self.settings)
        self.id2table = {}

    def __del__(self):
        pygame.mixer.quit()

    def settingsUpdated(self, settings):
        self.verbose = settings.headerGetInt("/settings/@verbose")
        self.datadir = settings.headerGet("/settings/data/@path")
        self.event2sound = None
        if ( settings.headerGet("/settings/sound") == "yes" or
             settings.headerGet("/settings/sound") == "on" ):
            sounddir = settings.headerGet("/settings/data/@sounds")
            #
            # Load event to sound map
            #
            self.event2sound = {}
            for (event, file) in self.config.headerGetProperties("/sequence/sounds")[0].iteritems():
                soundfile = sounddir + "/" + file
                if exists(soundfile):
                    sound = pygame.mixer.Sound(sounddir + "/" + file)
                    self.event2sound[event] = sound
                else:
                    self.error(soundfile + " file does not exist")

    def message(self, string):
        print "[PokerDisplay2D] " + string

    def error(self, string):
        self.message("ERROR " + string)

    def setProtocol(self, protocol):
        PokerDisplay.setProtocol(self, protocol)
        window = self.glade.get_widget("game_window")
        interface = self.factory.interface
        (width, height) = window.size_request()
        x = ( interface.width - width ) / 2
        y = ( interface.height - height ) / 2
        interface.screen.put(window, x, y)
        self.accelerators()
        window.show()
        
    def accelerators(self):
        action_group = gtk.AccelGroup()
        for key in self.settings.headerGetProperties('/settings/keys/key'):
            name = key['name']
            letter = key['control_key']
            if self.verbose > 1: self.message(name + " is bound to Ctrl+" + letter)
            self.actions[name].add_accelerator("clicked", action_group, gtk.gdk.keyval_from_name(letter), gtk.gdk.CONTROL_MASK, gtk.ACCEL_VISIBLE)
        self.factory.interface.window.add_accel_group(action_group)

    def init(self):
        settings = self.settings
        config = self.config
        gtkrc = self.datadir + "/interface/gtkrc"
        if exists(gtkrc):
            gtk.rc_parse(gtkrc)
        glade_file = self.datadir + "/interface/interface2d.glade"
        self.glade = gtk.glade.XML(fname = glade_file, root = "game_window")
        self.actions = {
            "call": self.glade.get_widget("call"),
            "raise": self.glade.get_widget("raise"),
            "raise_range": self.glade.get_widget("raise_range"),
            "raise_increase": self.glade.get_widget("raise_increase"),
            "raise_decrease": self.glade.get_widget("raise_decrease"),
            "raise_increase_bb": self.glade.get_widget("raise_increase_bb"),
            "raise_decrease_bb": self.glade.get_widget("raise_decrease_bb"),
            "raise_pot": self.glade.get_widget("raise_pot"),
            "raise_half_pot": self.glade.get_widget("raise_half_pot"),
            "check": self.glade.get_widget("check"),
            "fold": self.glade.get_widget("fold"),
            }
        self.switch = self.glade.get_widget("switch")
        self.glade.signal_autoconnect(self)
#        self.actions['check'].add_accelerator("clicked", gtk.AccelGroup(), gtk.gdk.keyval_from_name("p"), gtk.gdk.MOD1_MASK, gtk.ACCEL_VISIBLE)

        self.animations = pokeranimation2d.create(self.glade, config, settings)
        
    def on_switch_clicked(self, button):
        self.renderer.rotateTable()

    def on_sit_clicked(self, button):
        seat = int(button.get_name()[-1])
        protocol = self.protocol
        self.renderer.getSeat(PacketPokerSeat(game_id = protocol.getCurrentGameId(),
                                              serial = protocol.getSerial(),
                                              seat = seat))

    def on_quit_clicked(self, button):
        self.renderer.wantToLeave()

    def on_rebuy_clicked(self, button):
        protocol = self.protocol
        self.renderer.changeState("user_info", "rebuy", self.factory.getGame(protocol.getCurrentGameId()))

    def on_fold_clicked(self, button):
        protocol = self.protocol
        self.renderer.interactorSelected(PacketPokerFold(game_id = protocol.getCurrentGameId(),
                                                         serial = protocol.getSerial()))
    
    def on_check_clicked(self, button):
        protocol = self.protocol
        self.renderer.interactorSelected(PacketPokerCheck(game_id = protocol.getCurrentGameId(),
                                                          serial = protocol.getSerial()))
    
    def on_call_clicked(self, button):
        protocol = self.protocol
        self.renderer.interactorSelected(PacketPokerCall(game_id = protocol.getCurrentGameId(),
                                                         serial = protocol.getSerial()))

    def on_raise_increase_clicked(self, button):
        #
        # There seem to be a gtk bug when the slider displacement for a given
        # value is less than a pixel. In this case the slider does not have to move
        # which is normal. However, it seems to have a undesirable side effect : the
        # displayed value is not updated.
        #
        range = self.actions['raise_range']
        adjustment = range.get_adjustment()
        range.set_value(range.get_value() + adjustment.get_property('step-increment'))

    def on_raise_decrease_clicked(self, button):
        range = self.actions['raise_range']
        adjustment = range.get_adjustment()
        range.set_value(range.get_value() - adjustment.get_property('step-increment'))

    def on_raise_increase_bb_clicked(self, button):
        game_id = self.protocol.getCurrentGameId()
        bb = self.id2table[game_id].game.bigBlind()
        if bb:
            range = self.actions['raise_range']
            range.set_value(range.get_value() + (bb / 100.0))

    def on_raise_decrease_bb_clicked(self, button):
        game_id = self.protocol.getCurrentGameId()
        bb = self.id2table[game_id].game.bigBlind()
        if bb:
            range = self.actions['raise_range']
            range.set_value(range.get_value() - (bb / 100.0))

    def on_raise_pot_clicked(self, button):
        game_id = self.protocol.getCurrentGameId()
        bet_limit = self.id2table[game_id].bet_limit
        range = self.actions['raise_range']
        adjustment = range.get_adjustment()
        range.set_value(min(adjustment.get_property('upper'), bet_limit.pot / 100.0))

    def on_raise_half_pot_clicked(self, button):
        game_id = self.protocol.getCurrentGameId()
        bet_limit = self.id2table[game_id].bet_limit
        range = self.actions['raise_range']
        adjustment = range.get_adjustment()
        range.set_value(min(adjustment.get_property('upper'), ( bet_limit.pot / 2.0 ) / 100.0))

    def on_raise_clicked(self, button):
        raise_range = self.actions["raise_range"]
        protocol = self.protocol
        self.renderer.interactorSelected(PacketPokerRaise(game_id = protocol.getCurrentGameId(),
                                                          serial = protocol.getSerial(),
                                                          amount = int(raise_range.get_value() * 100)))

    def on_raise_range_value_changed(self, raise_range):
        value = int(raise_range.get_value() * 100)
        game_id = self.protocol.getCurrentGameId()
        bet_limit = self.id2table[game_id].bet_limit
        remainder = value % bet_limit.step
        if remainder:
            value -= remainder
            raise_range.set_value(value / 100.0)

    def deleteTable(self, game_id):
        table = self.id2table[game_id]
        del table.display
        del table.glade
        del self.id2table[game_id]

    def updateAction(self, packet):
        game_id = self.protocol.getCurrentGameId()
        game = self.factory.getGame(game_id)
        serial = self.protocol.getSerial()
        table = self.id2table[game_id]

        if not packet.style:
            self.actions[packet.name].hide()
            if packet.name == "raise":
                self.actions["raise_range"].hide()
            return
                
        if packet.name == "check" or packet.name == "fold" or packet.name == "call" or packet.name == "raise":
            action = self.actions[packet.name]
            action.show()
            action.set_label(packet.style)
            if packet.name == "raise":
                range = self.actions['raise_range']
                bet_limit = table.bet_limit
                range.set_value(bet_limit.min / 100.0)
                if bet_limit.min != bet_limit.max:
                    range.show()
                    if packet.selection and packet.selection.type == PACKET_POKER_RAISE:
                        self.updateRaiseRange(packet.selection.amount / 100.0)
                    else:
                        self.updateRaiseRange(bet_limit.min / 100.0)
                else:
                    range.hide()
        else:
            self.error("updateAction %s: unexpected name " % packet.name)

    def updateRaiseRange(self, selected_amount):
        range = self.actions['raise_range']
        if range.get_property('visible'):
            game_id = self.protocol.getCurrentGameId()
            game = self.factory.getGame(game_id)
            serial = self.protocol.getSerial()
            table = self.id2table[game_id]

            bet_limit = table.bet_limit
            range.set_range(bet_limit.min / 100.0, bet_limit.max / 100.0)
            range.set_increments(bet_limit.step / 100.0, bet_limit.step / 100.0)
            if selected_amount:
                range.set_value(selected_amount / 100.0)

    def render(self, packet):
        if self.verbose > 3: self.message(str(packet))

        if packet.type == PACKET_QUIT:
            reactor.stop()
            return

        if not self.protocol or not self.protocol.getCurrentGameId():
            return

        if self.event2sound:
            soundfile = self.event2sound.get(PacketNames[packet.type], None)
            playsound = False
            if soundfile:
                if ( packet.type == PACKET_POKER_TIMEOUT_WARNING or
                     packet.type == PACKET_POKER_TIMEOUT_NOTICE ):
                    if packet.serial == self.protocol.getSerial():
                        playsound = True
                else:
                    playsound = True
            if playsound:
                soundfile.play()
            
        game = self.factory.packet2game(packet)
        if game:
            self.id2table[game.id].render(packet)
            
        elif packet.type == PACKET_POKER_DISPLAY_NODE:
            self.updateAction(packet)
            
        elif packet.type == PACKET_POKER_TABLE:
            if not self.id2table.has_key(packet.id):
                self.id2table[packet.id] = PokerTable2D(packet, self)
            self.id2table[packet.id].reset()

        elif packet.type == PACKET_POKER_TABLE_QUIT:
            self.deleteTable(packet.id)
            
        elif packet.type == PACKET_POKER_TABLE_DESTROY:
            self.deleteTable(packet.game_id)

        elif packet.type == PACKET_POKER_CURRENT_GAMES:
            if packet.count < 2:
                self.switch.hide()
            else:
                self.switch.show()

        elif packet.type == PACKET_POKER_CHAT_HISTORY:
            if packet.show == "yes":
                self.renderer.chatHistoryShow()
            else:
                self.renderer.chatHistoryHide()


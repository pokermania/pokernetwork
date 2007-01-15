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
import gtk

from pprint import pprint
from pokerui.pokeranimation import *
from pokerengine.pokerchips import PokerChips

class Animation:
    def __init__(self, *args, **kwargs):
        self.timer = None
        self.timer_end = None
        self.scheduled = False
        self.running = False
        self.end_callbacks = []
        self.step = kwargs.get("step", 0.1)
        self.verbose = kwargs.get("verbose", 0)

    def message(self, string):
        print "[Animation] " + string

    def error(self, string):
        self.message("ERROR " + string)
        
    def endCallback(self, callback):
        if callback not in self.end_callbacks:
            self.end_callbacks.append(callback)
            
    def schedule(self, delay, duration, *args, **kwargs):
        self.stop()
        self.scheduled = True
        self.duration = duration
        self.args = args
        self.kwargs = kwargs
        if self.verbose > 2:
            self.message("schedule %d" % delay)
        self.timer = reactor.callLater(delay, self._start, duration, *args, **kwargs)

    def start(self, *args, **kwargs):
        pass
    
    def _start(self, duration, *args, **kwargs):
        self.stop()
        self.duration = duration
        self.running = True
        self.timer_end = reactor.callLater(self.duration, self.end, *args, **kwargs)
        self.start_time = time()
        self.current_time = time()
        self.end_time = time() + duration
        self.start(*args, **kwargs)
        if self.verbose > 2:
            self.message("_start %d" % duration)
        self._run(*args, **kwargs)

    def run(self, delta, *args, **kwargs):
        pass
    
    def _run(self, *args, **kwargs):
        delta = time() - self.current_time
        self.current_time += delta
        self.fraction_from_start = ( self.current_time - self.start_time ) / self.duration
        self.fraction_to_end = 1.0 - self.fraction_from_start
        self.run(delta, *args, **kwargs)
        now = time()
        next_time = min(self.end_time, now + self.step)
        if next_time > self.end_time:
            next_time = self.end_time
        delay = next_time - now
        if delay > 0.0:
            self.timer = reactor.callLater(delay, self._run, *args, **kwargs)
        else:
            self.stop()

    def end(self, *args, **kwargs):
        pass
        
    def stop(self):
        was_running = self.running
        self.scheduled = False
        self.running = False
        if self.timer and self.timer.active():
            self.timer.cancel()
        self.timer = None
        if self.timer_end and self.timer_end.active():
            self.timer_end.cancel()
        self.timer_end = None
        if was_running:
            self.end(*self.args, **self.kwargs)
            for callback in self.end_callbacks:
                callback()

class AnimationMoveWidget(Animation):

    def __init__(self, *args, **kwargs):
        Animation.__init__(self, *args, **kwargs)
        self.widget = kwargs.get("widget", None)
        self.fixed = kwargs.get("fixed", None)
        self.position_start = kwargs.get("position_start", (0, 0))
        self.position_end = kwargs.get("position_end", (0, 0))
        self.start_to_end = ( self.position_end[0] - self.position_start[0],
                              self.position_end[1] - self.position_start[1] )
        if self.verbose > 2:
            self.message(" start = %s, end = %s, start_to_end = %s" % ( self.position_start, self.position_end, self.start_to_end ))

    def start(self, *args, **kwargs):
        self.widget.show()
        self.fixed.put(self.widget, self.position_start[0], self.position_start[1])

    def run(self, delta, *args, **kwargs):
        start_to_end = ( self.start_to_end[0] * self.fraction_from_start,
                         self.start_to_end[1] * self.fraction_from_start )
        position = ( self.position_start[0] + start_to_end[0],
                     self.position_start[1] + start_to_end[1] )
        self.fixed.move(self.widget, int(position[0]), int(position[1]))
    
    def end(self, *args, **kwargs):
        self.fixed.remove(self.widget)
    
class AnimationBlinkWidget(Animation):

    blink_time = 0.5
    
    def __init__(self, *args, **kwargs):
        Animation.__init__(self, *args, **kwargs)
        self.widget = kwargs.get("widget", None)
        self.elapsed = 0.0

    def start(self, *args, **kwargs):
        self.widget.show()
        self.visible = True

    def run(self, delta, *args, **kwargs):
        self.elapsed += delta
        if self.elapsed > self.blink_time:
            self.elapsed -= self.blink_time
            if self.visible:
                self.visible = False
                self.widget.hide()
            else:
                self.visible = True
                self.widget.show()
    
    def end(self, *args, **kwargs):
        self.visible = True
        self.widget.show()
    
class PokerAnimationPlayer2D(PokerAnimationPlayer):
    
    def init(self):
        renderer = self.table.scheduler.animation_renderer
        screen = self.table.screen
        widget = renderer.get_widget("bet_seat%d" % self.seat)
        self.widget_bet = ( widget,
                            screen.child_get_property(widget, "x"),
                            screen.child_get_property(widget, "y") )
        widget = renderer.get_widget("name_seat%d" % self.seat)
        self.widget_name = ( widget,
                             screen.child_get_property(widget, "x"),
                             screen.child_get_property(widget, "y") )
        self.animations = []

    def message(self, string):
        print "[PokerAnimationPlayer2D] " + string

    def error(self, string):
        self.message("ERROR " + string)
        
    def animationRegister(self, animation):
        if animation not in self.animations:
            animation.endCallback(lambda: self.animationUnregister(animation))
            self.animations.append(animation)
        else:
            self.error("animation %s already registered" % animation)

    def animationUnregister(self, animation):
        if animation in self.animations:
            self.animations.remove(animation)
        else:
            self.error("animation %s not registered" % animation)
            
    def stopAll(self):
        PokerAnimationPlayer.stopAll(self)
        for animation in self.animations: animation.stop()

    def initStateAnimation(self):
        if self.verbose > 1: self.message(":initStateAnimation: not implemented")
        
    def playerArrive(self):
        if self.verbose > 1: self.message(":playerArrive: not implemented")

    def isInPosition(self):
        if self.verbose > 1: self.message(":isInPosition: not implemented")
    
    def setAnimationCallback(self, animation, callback):
        animation.endCallback(callback)

    def sitin(self):
        ( name, name_x, name_y ) = self.widget_name
        ( bet, bet_x, bet_y ) = self.widget_bet
        label = gtk.Label()
        label.set_text("sit")
        sit = gtk.EventBox()
        sit.add(label)
        sit.set_name("animation_sit")
        sit.show_all()
        animation = AnimationMoveWidget(fixed = self.table.screen,
                                        position_start = ( name_x, name_y ),
                                        position_end = ( bet_x, bet_y ),
                                        widget = sit,
                                        verbose = self.table.verbose)
        self.animationRegister(animation)
        animation.schedule(0, 2)
        return animation
    
    def sitout(self):
        ( name, name_x, name_y ) = self.widget_name
        ( bet, bet_x, bet_y ) = self.widget_bet
        label = gtk.Label()
        label.set_text("sit out")
        sit_out = gtk.EventBox()
        sit_out.add(label)
        sit_out.set_name("animation_sit")
        sit_out.show_all()
        animation = AnimationMoveWidget(fixed = self.table.screen,
                                        position_start = ( bet_x, bet_y ),
                                        position_end = ( name_x, name_y ),
                                        widget = sit_out,
                                        verbose = self.table.verbose)
        self.animationRegister(animation)
        animation.schedule(0, 2)
        return animation

    def check(self):
        if self.verbose > 1: self.message(":check: not implemented")

    def bet(self,game_id,chips):
        if self.verbose > 1: self.message(":bet: not implemented")

    def timeoutWarning(self):
        if self.verbose > 1: self.message(":timeoutWarning: not implemented")

    def pot2player(self, packet):
        if self.verbose > 2: self.message("pot2player: move %s from %s to %s" % ( packet.chips, self.table.widget_pots[packet.pot], self.widget_bet))
        value = 0
        while packet.chips:
            chip_value = packet.chips.pop(0)
            count = packet.chips.pop(0)
            value += chip_value * count

        ( pot, pot_x, pot_y ) = self.table.widget_pots[packet.pot]
        ( bet, bet_x, bet_y ) = self.widget_bet
        label = gtk.Label()
        label.set_text(PokerChips.tostring(value))
        player_pot = gtk.EventBox()
        player_pot.add(label)
        player_pot.set_name("animation_sit")
        player_pot.show_all()
        animation = AnimationMoveWidget(fixed = self.table.screen,
                                        position_start = ( pot_x, pot_y ),
                                        position_end = ( bet_x, bet_y ),
                                        widget = player_pot,
                                        verbose = self.table.verbose)
        self.animationRegister(animation)
        animation.schedule(0, 2)
        return animation

    def showdownDelta(self, delta, is_delta_max, is_delta_min, chips):
        if self.verbose > 2: self.message("delta %d, is_delta_max %s, is_delta_min %s" % (delta, is_delta_max, is_delta_min))
        if is_delta_max:
            animation = AnimationBlinkWidget(widget = self.widget_name[0],
                                             verbose = self.table.verbose)
            self.animationRegister(animation)
            animation.schedule(0, 3)
        ( bet, bet_x, bet_y ) = self.widget_bet
        if delta < 0:
            down = gtk.Image()
            down.set_from_stock(gtk.STOCK_GOTO_BOTTOM, gtk.ICON_SIZE_SMALL_TOOLBAR)
            animation = AnimationMoveWidget(fixed = self.table.screen,
                                            position_start = ( bet_x, bet_y ),
                                            position_end = ( bet_x, bet_y + 10 ),
                                            widget = down,
                                            verbose = self.table.verbose)
            self.animationRegister(animation)
            animation.schedule(0, 3)
        else:
            up = gtk.Image()
            up.set_from_stock(gtk.STOCK_GOTO_TOP, gtk.ICON_SIZE_SMALL_TOOLBAR)
            animation = AnimationMoveWidget(fixed = self.table.screen,
                                            position_start = ( bet_x, bet_y ),
                                            position_end = ( bet_x, bet_y - 10 ),
                                            widget = up,
                                            verbose = self.table.verbose)
            self.animationRegister(animation)
            animation.schedule(0, 3)

    def pot2playerAnimate(self):
        pass
    
    def fold(self, game_id):
        PokerAnimationPlayer.fold(self, game_id)
        if self.verbose > 1: self.message(":fold: not implemented")
    
    def chat(self, packet):
        if self.verbose > 1: self.message(":chat: not implemented")

class PokerAnimationTable2D(PokerAnimationTable):

    def __init__(self, *args, **kwargs):
        PokerAnimationTable.__init__(self, *args, **kwargs)
        self.PokerAnimationPlayerType = PokerAnimationPlayer2D
        renderer = self.scheduler.animation_renderer
        self.screen = renderer.get_widget("game_window_fixed")
        self.widget_pots = []
        for pot in map(lambda x: renderer.get_widget("pot%d" % x), xrange(9)):
            self.widget_pots.append((pot, self.screen.child_get_property(pot, "x"), self.screen.child_get_property(pot, "y")))

class PokerAnimationScheduler2D(PokerAnimationScheduler):
    def __init__(self, *args, **kwargs):
        PokerAnimationScheduler.__init__(self, *args, **kwargs)
        self.PokerAnimationPlayerType = PokerAnimationPlayer2D
        self.PokerAnimationTableType = PokerAnimationTable2D

def create(animation_renderer, config, settings):
    return PokerAnimationScheduler2D(animation_renderer = animation_renderer,
                                     config = config,
                                     settings = settings)

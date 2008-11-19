#
# Copyright (C) 2008 Loic Dachary <loic@dachary.org>
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
#  Johan Euphrosine <johan@mekensleep.org>
#  Loic Dachary <loic@gnu.org>
#


class state:
    def __init__(self):
        self.changed = False
        self.clicked = None
        self.default = None

    def enter(self, i):
        self.updateTags(i)
        self.changed = True

    def update(self, i):
        pass

    def leave(self, i):
        pass

    def updateTags(self, i):
        pass

    def setClicked(self, tag):
        if tag != self.clicked:
            self.clicked = tag
            self.changed = True

    def setDefault(self, tag):
        if tag != self.clicked:
            self.default = tag
            self.changed = True

    def getDefault(self):
        return self.default

    def getClicked(self):
        return self.clicked

class enabled(state):
    name = "enabled"

    def updateTags(self, i):
        self.setDefault("enabled_default")
        self.setClicked(i.inPosition and "enabled_clicked_in_position" or "enabled_clicked")

    def update(self, i):
        if i.getSelected():
            if i.inPosition:
                i.setState(activated())
            else:
                i.setState(scheduled())
        #self.updateTags(i)

class scheduled(state):
    name = "scheduled"
    def updateTags(self, i):
        self.setDefault("scheduled_default")
        self.setClicked("scheduled_clicked")

    def update(self,i):
        if i.getSelected():
            if not i.inPosition:
                i.setState(enabled())
            return
        if i.getCanceled():
            i.setState(enabled())
            return
        if i.inPosition:
            i.setState(activated())
            return

class activated(state):
    name = "activated"
    def updateTags(self, i):
        self.setDefault("activated_default")
        self.setClicked("activated_clicked")

    def enter(self, i):
        state.enter(self, i)
        i.action()

    def update(self, i):
        #should it be in interactor class instead ?
        if not i.inPosition:
            i.setState(disabled())

class disabled(state):
    name = "disabled"
    def updateTags(self, i):
        self.setDefault(None)
        self.setClicked(None)

class PokerInteractorSet:
    def __init__(self, *args, **kwargs):
        self.items = kwargs
        
class PokerInteractor:
    "Poker interactors logic"

    selected = 0
    canceled = 0
    state = 0
    inPosition = 0
    name = ""
    actionCallback = 0
    displayCallback = 0
    selectCallback = 0
#    def __init__(self, name):
#        self.name = name
#        self.setState(self.disabled())
#        return
    def __init__(self, name, action, display, select, nameMap, game_id, verbose = 0, prefix = ""):
        self.name = name
        self.actionCallback = action
        self.displayCallback = display
        self.selectCallback = select
        self.userData = None
        self.nameMap = nameMap
        self.game_id = game_id
        self.verbose = verbose
        self.selected_value = None
        self.prefix = prefix

        self.state = disabled()
        self.state.enter(self)
        self.changed = True
        self.update()        

    def error(self, string):
        self.message("ERROR " + string)
        
    def message(self, string):
        print string
        
    def setUserData(self, userData):
        if self.userData != userData:
            self.userData = userData
            self.changed = True
            self.setSelectedValue(None)
            self.cancel()
        self.userData = userData

    def getUserData(self):
        return self.userData
    
    def setSelectedValue(self, value):
        if self.selected_value != value:
            self.selected_value = value
            self.changed = True
        self.selected_value = value

    def getSelectedValue(self):
        value = self.selected_value
        if value != None:
            self.selected_value = None
            self.changed = True
        return value
    
    def getDefault(self):
        return self.nameMap.get(self.state.getDefault(), "")

    def getClicked(self):
        return self.nameMap.get(self.state.getClicked(), "")
    
    def setInPosition(self, value):
        #print "setInPosition: %i" % value
        if self.inPosition != value:
            self.inPosition = value
            self.changed = True

    def toggle(self):
        self.setSelected(self.selected and 0 or 1)

    def select(self, value):
        self.setSelectedValue(value)
        self.setSelected(1)
        self.selectCallback(self)

    def setSelected(self, value):
        if self.selected != value:
            self.selected = value
            self.changed = True

    def getSelected(self):
        value = self.selected
        self.selected = 0
        if value:
            self.changed = True
        return value
    
    def cancel(self):
        self.setCanceled(1)

    def setCanceled(self, value):
        if self.canceled != value:
            self.canceled = value
            self.changed = True

    def getCanceled(self):
        value = self.canceled
        self.canceled = 0
        if value:
            self.changed = True
        return value

    def setState(self, value):
        #consume event
        if value.name != self.state.name:
            self.getSelected()
            self.getCanceled()
            fromState = self.state
            toState = value
            if fromState:
                fromState.leave(self)
            if toState:
                toState.enter(self)
    #        print "[setState %s -> %s]" % (fromState, toState)
            self.state = value
            self.changed = True
    
    def disable(self):
        self.setCanceled(0)
        self.setSelected(0)
        self.setSelectedValue(None)
        self.setInPosition(0)
        self.setUserData(None)
        self.setState(disabled())

    def setEnableIfDisabled(self):
        if self.state.name == "disabled":
            self.setState(enabled())

    def setEnableIfActivated(self):
        if self.state.name == "activated":
            self.setState(enabled())

    def isDisabled(self):
        return self.state.name == "disabled"
    
    def isActive(self):
        return self.state.name == "activated"
        
    def update(self):        
        if self.changed:
            if self.verbose > 3:
                self.message(self.prefix + " PokerInteractor::update: before " + self.name + ": state " + self.state.name + ", canceled " + str(self.canceled) + ", selected " + str(self.selected) + ", inPosition " + str(self.inPosition) + ", userData " + str(self.userData))
            self.state.update(self)
            if self.verbose > 3:
                self.message(self.prefix + "                         after  " + self.name + ": state " + self.state.name + ", canceled " + str(self.canceled) + ", selected " + str(self.selected) + ", inPosition " + str(self.inPosition) + ", userData " + str(self.userData))
            self.displayCallback(self)
            self.changed = False
            self.state.changed = False

    def stateHasChanged(self):
        return self.state.changed

    def hasChanged(self):
        return self.state.changed or self.changed
    
    def action(self):
        self.actionCallback(self)

if __name__ == "__main__":
    print "poker interactor unit test"
    def action(interactor):
        print "action callback"
    def display(interactor):
        print "display callback"
        if interactor.state.changed:
            print "   clicked " + interactor.getClicked() + ", default " + interactor.getDefault()
    def selected(interactor):
        print "selected callback"
    interactor = PokerInteractor("test", action, display, selected, 1)
    interactor.update()
    print "enable()"
    interactor.enable()
    interactor.update()
    print "select()"
    interactor.select()
    interactor.update()
    interactor.update()
    print "setInPosition(1)"
    interactor.setInPosition(1)
    interactor.update()
    interactor.update()
    print "setInPosition(0)"
    interactor.setInPosition(0)
    interactor.update()
    interactor.update()
    interactor.toggle()
    interactor.update()
    interactor.toggle()
    interactor.update()
    interactor.update()

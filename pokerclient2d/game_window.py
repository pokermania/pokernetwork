import gtk
import unittest

def vbox(*widgets, **kwargs):
    vbox = gtk.VBox(False, 5)
    map(vbox.add, widgets)
    return vbox

def hbox(*widgets, **kwargs):
    hbox = gtk.HBox(False, 5)
    map(hbox.add, widgets)
    return hbox

def align_center(widget):
    align = gtk.Alignment()
    align.set_property("xalign", 0.5)
    align.set_property("yalign", 0.5)
    align.add(widget)
    return align

def align_left(widget):
    align = gtk.Alignment()
    align.set_property("xalign", 0.0)
    align.set_property("yalign", 0.5)
    align.add(widget)
    return align    

def align_right(widget):
    align = gtk.Alignment()
    align.set_property("xalign", 1.0)
    align.set_property("yalign", 0.5)
    align.add(widget)
    return align    
    
def seat_widget_up(player, showdown, dealer):    
    return vbox(align_center(player), 
		align_center(showdown),
		align_center(dealer))

def seat_widget_down(player, showdown, dealer):
    return vbox(align_center(dealer),
		align_center(showdown),
		align_center(player))

def seat_widget_up_left(player, showdown, dealer):
    return vbox(align_left(player),
		hbox(showdown, align_center(dealer)))


def seat_widget_down_left(player, showdown, dealer):
    return vbox(hbox(showdown, align_center(dealer)),
		align_left(player))

def seat_widget_up_right(player, showdown, dealer):
    return vbox(align_right(player),
		hbox(align_center(dealer), showdown))

def seat_widget_down_right(player, showdown, dealer):
    return vbox(hbox(align_center(dealer), align_center(showdown)),
		align_right(player))
#    vbox = gtk.VBox(False, 5)
#    hbox = gtk.HBox(False, 5)
#    vbox.add(hbox)
#    sub_vbox = gtk.VBox()
#    hbox.add(sub_vbox)
#    sub_vbox.add(align_center(bet))
#    sub_vbox.add(align_center(dealer))
#    hbox.add(align_center(showdown))
#    vbox.add(align_right(player))
    return vbox


def player_name_widget(name):
    player_label = gtk.Label()
    player_label.set_label("proppy")
    color = gtk.gdk.color_parse("#ffffff")
    player_label.modify_fg(gtk.STATE_NORMAL, color)
    player_label.modify_fg(gtk.STATE_ACTIVE, color)
    player_label.set_name(name)
    return player_label

def player_stack_widget(name):
    stack_label = gtk.Label()
    stack_label.set_label("100$")
    color = gtk.gdk.color_parse("#ffc600")
    stack_label.modify_fg(gtk.STATE_NORMAL, color)
    stack_label.modify_fg(gtk.STATE_ACTIVE, color)
    stack_label.set_name(name)
    return stack_label    
    
def player_widget(player_name, player_stack):
    event_box = gtk.EventBox()
    event_box.set_name("player")
    event_box.set_size_request(102, 101)
    
    alignment = gtk.Alignment()
    alignment.set_property("xalign", 0.5)
    alignment.set_property("yalign", 0.5)
    alignment.set_property("top-padding", 6)
    alignment.set_property("bottom-padding", 6)
    event_box.add(alignment)
    
    vbox = gtk.VBox()
    alignment.add(vbox)
    
    image = gtk.Image()
    image.set_from_file("data/skin/Kspades.png")
    vbox.add(image)
    
    #vbox.add(player_name)
    vbox.add(player_stack)
    return event_box

def table_widget():
    box = gtk.EventBox()
    box.set_name("table")
    box.set_size_request(577, 284)
    return box


def card_widget(name):
    image = gtk.Image()
    image.set_from_file("data/skin/Kdiamonds.png")
    image.set_name(name)
    return image
    
def showdown_widget(cards):
    fixed = gtk.Fixed()

    for i in range(0,len(cards)):
	card = cards[i]
	fixed.put(card, i*10, 0)
    return fixed

def bet_widget(name):
    button = gtk.Button()
    button.set_sensitive(False)
    button.set_size_request(34, 34)
    button.set_label("$150")
    button.set_alignment(0.5, 0.6)
    button.set_name(name)
    return button


def winner_widget(name):
    label = gtk.Label()
    label.set_name(name)
    label.set_label("Five of a kind")
    return label

def board_widget(cards, winners):
    root = gtk.Alignment()
    root.set_property("xalign", 0.5)
    root.set_property("yalign", 0.5)

    vbox = gtk.VBox()
    root.add(vbox)
    vbox.set_name("board")

    hbox = gtk.HBox()
    vbox.add(hbox)
    map(hbox.add, cards)

    map(vbox.add, winners)

    return root


def pot_widget(name):
    button = gtk.Button()
    button.set_sensitive(False)
    button.set_name("pot")
    button.set_size_request(34, 34)
    button.set_label("$150")
    button.set_alignment(0.5, 0.6)
    button.set_name(name)
    return button
    
def pots_widget(pots):    
    hbox = gtk.HBox()
    for pot in pots:
	hbox.add(pot)
    return hbox

def switch_table_widget():
    box = gtk.EventBox()
    box.set_name("switch")
    box.set_size_request(139, 52)

    alignment = gtk.Alignment()
    box.add(alignment)
    alignment.set_property("xalign", 0.5)
    alignment.set_property("yalign", 0.5)
    alignment.set_property("top-padding", 20)
    hbox = gtk.HBox()
    alignment.add(hbox)
    parent = None
    for i in range(0, 5):
	radio_alignment = gtk.Alignment()
	radio_alignment.set_property("xalign", 0.5)
	radio_alignment.set_property("yalign", 0.5)
	hbox.add(radio_alignment)

	radio = gtk.RadioButton(parent)
	radio_alignment.add(radio)
	radio.set_property("draw-indicator", False)
	radio.set_name("radio%d" % (i+1))
	radio.set_relief(gtk.RELIEF_NORMAL)
	radio.set_size_request(21, 21)
	parent = radio
    
    return box

def quit_widget():
    button = gtk.Button()
    button.set_size_request(67, 26)
    button.set_name("quit")
    return button

def rebuy_widget():
    button = gtk.Button()
    button.set_size_request(67, 26)
    button.set_name("rebuy")
    return button

def table_action_widget(quit, rebuy, switch):
    vbox = gtk.VBox(False, 5)
    hbox = gtk.HBox(False, 5)
    vbox.add(hbox)
    hbox.add(align_center(quit))
    hbox.add(align_center(rebuy))
    vbox.add(switch)
    return vbox

def check_widget():
    button = gtk.Button()
    button.set_size_request(44, 30)
    button.set_name("check")
    return button

def fold_widget():
    button = gtk.Button()
    button.set_size_request(44, 30)
    button.set_name("fold")
    return button

def call_widget():
    button = gtk.Button()
    button.set_size_request(44, 30)
    button.set_name("call")
    return button

def raise_widget():
    button = gtk.Button()
    button.set_size_request(44, 30)
    button.set_name("raise")
    return button

def dealer_widget(name):
    button = gtk.Button()
    button.set_sensitive(False)
    button.set_size_request(24, 24)
    button.set_name(name)
    return button

def raise_slider_widget():
    scale = gtk.HScale()
    scale.set_size_request(80, 10)
    scale.set_name("raise_range")
    scale.set_property("draw-value", False)
    scale.set_range(0, 100)
    scale.set_increments(1, 10)
    return scale
    
def game_action_widget(check, call, fold, raise_, raise_slider):
    vbox = gtk.VBox(False, 5)
    top_hbox = gtk.HBox(False, 5)
    vbox.add(top_hbox)
    for action in (check, call, fold):
	top_hbox.add(action)
    bottom_hbox = gtk.HBox(False, 5)
    vbox.add(bottom_hbox)
    alignment = gtk.Alignment()
    bottom_hbox.add(alignment)
    alignment.add(raise_)
    box = gtk.EventBox()
    bottom_hbox.add(box)
    box.set_name("raise_background")
    box.set_size_request(94, 50)
    slider_vbox = gtk.VBox()
    box.add(slider_vbox)
    slider_alignment = gtk.Alignment()
    slider_vbox.add(slider_alignment)
    slider_alignment.set_property("xalign", 0.5)
    slider_alignment.set_property("yalign", 0.7)
    slider_alignment.add(raise_slider)
    entry_alignment = gtk.Alignment()
    slider_vbox.add(entry_alignment)
    entry_alignment.set_property("xalign", 0.5)
    entry_alignment.set_property("yalign", 0.5)
    entry_alignment.set_property("left-padding", 12)
    entry_alignment.set_property("right-padding", 12)
    entry = gtk.Entry()
    entry_alignment.add(entry)
    entry.set_name("raise_text")
    entry.set_text("$100")
    entry.set_has_frame(False)
    entry.set_property("xalign", 0.5)
    return vbox

def sit_widget(name):
    button = gtk.Button()
    button.set_name(name)
    button.set_size_request(102, 101)
    return button

def table_status_widget(name):
    textview = gtk.TextView()
    textview.set_name(name)
    textview.set_size_request(200, 100)
    textview.get_buffer().set_text("table: aminche\nblind 100-100")
    return textview

def accelerator_widget(name):
    button = gtk.Button()
    button.set_name(name)
    button.set_size_request(1, 1)
    return button

class GameWindowGlade:
    def __init__(self):
	self.widgets = {}
	gtk.rc_parse("data/skin/gtkrc")
	game_toplevel = gtk.Window()
	game_toplevel.set_name("game_toplevel")
	game_toplevel.set_size_request(800, 600)
	game_toplevel.set_resizable(False)
	#self.set_widget(game_toplevel)
	game_window = gtk.EventBox()
	#game_toplevel.add(game_window)
	game_window.set_name("game_window")
	self.set_widget(game_window)

        alignment = gtk.Alignment()
	alignment.set_property("xalign", 0.5)
	alignment.set_property("yalign", 0.5)

	table = table_widget()
	alignment.add(table)
    
	fixed = gtk.Fixed()
	fixed.set_name("game_fixed")
	self.set_widget(fixed)
	game_window.add(fixed)

    
	width = 800
	height = 600
	x = (width-577)/2
	y = (height-284)/2
    
	#widget = player_widget()
	#widget.set_state(gtk.STATE_ACTIVE)
	#fixed.put(widget, 100, 100)
	seats = ((seat_widget_up, (width-102)/2, 10),
		 (seat_widget_up, (width-102)/2-102-35, 10),
		 (seat_widget_up, (width-102)/2+102+35, 10),
		 
		 (seat_widget_down, (width-102)/2, height-200),
		 (seat_widget_down, (width-102)/2-102-35, height-200),
		 (seat_widget_down, (width-102)/2+102+35, height-200),
		 
		 (seat_widget_up_left, 10, (height-101-101)/2-80),
		 (seat_widget_down_left, 10, (height-101+101)/2+30),
		 (seat_widget_up_right, (width-134-10), (height-101-101)/2-80),
		 (seat_widget_down_right, (width-134-10), (height-101+101)/2+30),
		 
		 (seat_widget_up, (width-102)/2, 10),
		 (seat_widget_up, (width-102)/2-102-35, 10),
		 (seat_widget_up, (width-102)/2+102+35, 10),
		 
		 (seat_widget_down, (width-102)/2, height-200),
		 (seat_widget_down, (width-102)/2-102-35, height-200),
		 (seat_widget_down, (width-102)/2+102+35, height-200),
		 
		 (seat_widget_up_left, 10, (height-101-101)/2-80),
		 (seat_widget_down_left, 10, (height-101+101)/2+30),
		 
		 (seat_widget_up_right, (width-134-10), (height-101-101)/2-80),
		 (seat_widget_down_right, (width-134-10), (height-101+101)/2+30),
		 )
	
	for seat in range(0, len(seats)):
	    (seat_widget, x, y) = seats[seat]
	    player_infos = (player_name_widget("name_seat%d" % seat),
			    player_stack_widget("money_seat%d" % seat))
	    map(self.set_widget, player_infos)
	    bet = bet_widget("bet_seat%d" % seat)
	    self.set_widget(bet)
	    cards = map(lambda card_index: 
			card_widget("card%d_seat%d" % (card_index, seat)), 
			range(1, 8))
	    map(self.set_widget, cards)

	    dealer = dealer_widget("dealer%d" % seat)
	    self.set_widget(dealer)

	    player = player_widget(*player_infos)
	    fixed.put(seat_widget(player, showdown_widget(cards), dealer), x, y)

	    sit = sit_widget("sit_seat%d" % seat)
	    self.set_widget(sit)
	    
	    fixed.put(bet, x, y)
	    fixed.put(player_infos[0], x, y)
	    fixed.put(sit, x-10, y-10)

	vbox = gtk.VBox()

	cards = map(lambda card_index: card_widget("board%d" % card_index), range(1, 6))
	map(self.set_widget, cards)
	
	winners = map(lambda winner_index: winner_widget("winner%d" % winner_index), range(9))
	map(self.set_widget, winners)
	vbox.add(board_widget(cards, winners))
	
	pots = map(lambda pot_index: pot_widget("pot%d" % pot_index), range(9))
	map(self.set_widget, pots)
	for pot in pots:
	    fixed.put(pot, 0, 0)
	#vbox.add(pots_widget(pots))
	
	fixed.put(vbox, 220, 240)
	table_actions = (quit_widget(), rebuy_widget(), switch_table_widget())
	map(self.set_widget, table_actions)
	fixed.put(table_action_widget(*table_actions), 0, 0)

	
	game_actions = (check_widget(),
			call_widget(),
			fold_widget(),
			raise_widget(),
			raise_slider_widget())
	map(self.set_widget, game_actions)
	fixed.put(game_action_widget(*game_actions), 600, 0)

	table_status = table_status_widget("table_status")
	fixed.put(table_status, 800-200, 600-100)
	self.set_widget(table_status)
	
	accelerators_name = ("raise_increase",
			     "raise_decrease",
			     "raise_increase_bb",
			     "raise_decrease_bb",
			     "raise_pot",
			     "raise_half_pot")
	accelerators = map(accelerator_widget, accelerators_name)
	map(lambda accelerator: fixed.put(accelerator, 0, 0), accelerators)
	map(self.set_widget, accelerators)
	
    def set_widget(self, widget):
	self.widgets[widget.get_name()] = widget
    def get_widget(self, name):
	return self.widgets[name]
    def relative_file(self, file):
	pass
    def signal_autoconnect(self, instance):
	pass

class GameWindowGladeTest(unittest.TestCase):
    def setUp(self):
	pass
    def tearDown(self):
	pass
    def test_getWidget(self):
	glade = GameWindowGlade()
	seat = 1
	name = glade.get_widget("name_seat%d" % seat)
	name.set_label("proppy")
        money = glade.get_widget("money_seat%d" % seat)
        money.set_label("$100")
        bet = glade.get_widget("bet_seat%d" % seat)
        bet.set_label("$100")
        cards = map(lambda x: glade.get_widget("card%d_seat%d" % ( x, seat )), xrange(1,8))
	cards[0].set_from_file("Kspades.png")
	#toplevel = glade.get_widget("game_toplevel")
        board = map(lambda x: glade.get_widget("board%d" % x), xrange(1,6))
	board[0].set_from_file("Kspades.png")
        pots = map(lambda x: glade.get_widget("pot%d" % x), xrange(9))
	pots[0].set_label("$100")
        dealer_buttons = map(lambda x: glade.get_widget("dealer%d" % x), xrange(10))
        winners = map(lambda x: glade.get_widget("winner%d" % x), xrange(9))
	winners[0].set_label("hi card")
        seats = map(lambda x: glade.get_widget("sit_seat%d" % x), xrange(10))
	seats[0].show()
	seats[0].hide()
        self.table_status = glade.get_widget("table_status").get_buffer()
        self.table_status.set_text("\n".join(("salut", "les", "aminches")))
	fixed = glade.get_widget("game_fixed")
	children = fixed.get_children()
	self.assert_(len(children) > 0)
        quit = glade.get_widget("quit")
	quit.hide()
	quit.show()
        rebuy = glade.get_widget("rebuy")
	rebuy.hide()
	rebuy.show()
	glade.get_widget("raise_increase").show() # 1x1 button used for accelerators
        glade.get_widget("raise_decrease").show() # 1x1 button used for accelerators
        glade.get_widget("raise_increase_bb").show() # 1x1 button used for accelerators
        glade.get_widget("raise_decrease_bb").show() # 1x1 button used for accelerators
        glade.get_widget("raise_pot").show() # 1x1 button used for accelerators
        glade.get_widget("raise_half_pot").show() # 1x1 button used for accelerators
	call = glade.get_widget("call")
	raise_ = glade.get_widget("raise")
	raise_range = glade.get_widget("raise_range")
	check = glade.get_widget("check")
	fold = glade.get_widget("fold")
	glade.relative_file("")
	glade.get_widget("switch")
	glade.signal_autoconnect(self)

	screen = glade.get_widget("game_fixed")
	widget_pots = []
        for pot in map(lambda x: glade.get_widget("pot%d" % x), xrange(9)):
            widget_pots.append((pot, screen.child_get_property(pot, "x"), screen.child_get_property(pot, "y")))
        for bet in map(lambda x: glade.get_widget("bet_seat%d" % x), xrange(10)):
            widget_pots.append((bet, screen.child_get_property(bet, "x"), screen.child_get_property(bet, "y")))
        for bet in map(lambda x: glade.get_widget("name_seat%d" % x), xrange(10)):
            widget_pots.append((bet, screen.child_get_property(bet, "x"), screen.child_get_property(bet, "y")))

if __name__ == '__main__':
    #glade = GameWindowGlade()
    #game_toplevel = glade.get_widget("game_toplevel")
    #game_toplevel.show_all()
    #gtk.main()
    unittest.main()

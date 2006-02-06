/*
 *
 * Copyright (C) 2005 Mekensleep
 *
 *	Mekensleep
 *	24 rue vieille du temple
 *	75004 Paris
 *       licensing@mekensleep.com
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301, USA.
 *
 * Authors:
 *  Loic Dachary <loic@gnu.org>
 */

#ifndef	_DISPATCHER_H_
#define	_DISPATCHER_H_


enum lobby_tab_state
  {
    none,
    lobby,
    tournament,
  };

int dispatcher(GtkLayout* screen);
int	handle_lobby(GladeXML* g_tournaments_xml, GladeXML* g_tournament_info_xml, GladeXML* g_lobby_tabs_xml, GladeXML* g_cashier_button_xml, GladeXML* g_clock_xml, GtkLayout* screen, int init);
int	handle_login(GladeXML* g_glade_xml, GtkLayout* screen, int init);
int	handle_message_box(GladeXML* g_glade_xml, GtkLayout* screen, int init);
int	handle_yesno(GladeXML* g_glade_xml, GtkLayout* screen, int init);
int	handle_hand_history(GladeXML* g_glade_xml, GtkLayout* screen, int init);
int	handle_chooser(GladeXML* g_glade_xml, GtkLayout* screen, int init);
int	handle_cashier(GladeXML* s_glade_personal_information_xml, GladeXML* s_glade_account_status_xml, GladeXML* s_glade_exit_cashier_xml, GtkLayout* screen, int init);
int	handle_blind(GladeXML* g_glade_xml, GtkLayout* screen, int init);
int	handle_sit_actions(GladeXML* g_glade_xml, GtkLayout* screen, int init);
int	handle_chat(GladeXML* g_history_xml, GladeXML* 	g_entry_xml, GtkLayout* screen, int init);
int	handle_tournaments(GladeXML* g_tournaments_xml, GladeXML* g_tournament_info_xml, GladeXML* g_lobby_tabs_xml, GladeXML* g_cashier_button_xml, GladeXML* g_clock_xml, GtkLayout* screen, int init);
int	handle_buy_in(GladeXML*	g_glade_xml, GtkLayout* screen, int init);
int handle_outfit(GladeXML* g_glade_outfit_sex_xml, GladeXML* g_glade_outfit_ok_xml, GladeXML* g_glade_outfit_slots_male_xml, GladeXML* g_glade_outfit_slots_female_xml, GladeXML* g_glade_outfit_params_xml, GladeXML* g_glade_outfit_random_xml, GtkLayout* screen, int init);
int	handle_menu(GladeXML* g_glade_xml, GtkLayout* screen, int init);

#endif /* _DISPATCHER_H_ */

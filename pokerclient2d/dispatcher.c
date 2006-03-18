/*
 *
 * Copyright (C) 2005, 2006 Mekensleep
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

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif /* HAVE_CONFIG_H */

#include <string.h>

#include <gtk/gtk.h>
#include <glade/glade.h>

#include "gui.h"
#include "interface_io.h"
#include "dispatcher.h"

int dispatcher(GtkLayout* screen) {
  char*	string = get_string();

  if (!string)
    {
      g_warning("null packet");
      return FALSE;
    }

  g_message("received %s", string);
  if(0)
    ;
  else if (strcmp("login", string) == 0)
    {
      static GladeXML*	g_glade_xml = 0;
      int init = 0;
      if(!g_glade_xml) {
        g_glade_xml = gui_load_widget("login_window");
        init = 1;
      }

      handle_login(g_glade_xml, screen, init);
    }
  else if (strcmp("message_box", string) == 0)
    {
      static GladeXML*	g_glade_xml = 0;
      int init = 0;
      if(!g_glade_xml) {
        g_glade_xml = gui_load_widget("message_window");
        init = 1;
      }

      handle_message_box(g_glade_xml, screen, init);
    }
  else if (strcmp("yesno", string) == 0)
    {
      static GladeXML*	g_glade_xml = 0;
      int init = 0;
      if(!g_glade_xml) {
        g_glade_xml = gui_load_widget("yesno_window");
        init = 1;
      }

      handle_yesno(g_glade_xml, screen, init);
    }
  else if (strcmp("muck", string) == 0)
    {
      static GladeXML*	g_glade_xml = 0;
      int init = 0;
      if(!g_glade_xml) {
        g_glade_xml = gui_load_widget("muck_window");
        init = 1;
      }

      handle_muck(g_glade_xml, screen, init);
    }
  else if (strcmp("check_warning", string) == 0)
    {
      static GladeXML*	g_glade_xml = 0;
      int init = 0;
      if(!g_glade_xml) {
        g_glade_xml = gui_load_widget("check_warning_window");
        init = 1;
      }

      handle_check_warning(g_glade_xml, screen, init);
    }
  else if (strcmp("hand_history", string) == 0)
    {
      static GladeXML*	g_glade_xml = 0;
      int init = 0;
      if(!g_glade_xml) {
        g_glade_xml = gui_load_widget("hand_history_window");
        init = 1;
      }

      handle_hand_history(g_glade_xml, screen, init);
    }
  else if (strcmp("chooser", string) == 0)
    {
      static GladeXML*	g_glade_xml = 0;
      int init = 0;
      if(!g_glade_xml) {
        g_glade_xml = gui_load_widget("chooser_window");
        init = 1;
      }

      handle_chooser(g_glade_xml, screen, init);
    }
  else if (strcmp("cashier", string) == 0)
    {
      static GladeXML*	s_glade_personal_information_xml = 0;
      static GladeXML*	s_glade_account_status_xml = 0;
      static GladeXML*	s_glade_exit_cashier_xml = 0;
      int init = 0;
      if(!s_glade_personal_information_xml) {
        s_glade_personal_information_xml = gui_load_widget("personal_information_window");
        s_glade_account_status_xml = gui_load_widget("account_status_window");
        s_glade_exit_cashier_xml = gui_load_widget("exit_cashier_window");
        init = 1;
      }

      handle_cashier(s_glade_personal_information_xml, s_glade_account_status_xml, s_glade_exit_cashier_xml, screen, init);
    }
  else if (strcmp("blind", string) == 0)
    {
      static GladeXML*	g_glade_xml = 0;
      int init = 0;
      if(!g_glade_xml) {
        g_glade_xml = gui_load_widget("blind_window");
        init = 1;
      }

      handle_blind(g_glade_xml, screen, init);
    }
  else if (strcmp("sit_actions", string) == 0)
    {
      static GladeXML*	g_glade_xml = 0;
      int init = 0;
      if(!g_glade_xml) {
        g_glade_xml = gui_load_widget("sit_actions_window");
        init = 1;
      }

      handle_sit_actions(g_glade_xml, screen, init);
    }
  else if (strcmp("chat", string) == 0)
    {
      static GladeXML* 	g_history_xml = 0;
      static GladeXML* 	g_entry_xml = 0;
      int init = 0;
      if(!g_history_xml) {
        g_history_xml = gui_load_widget("chat_history_window");
        g_entry_xml = gui_load_widget("chat_entry_window");
      
        init = 1;
      }

      handle_chat(g_history_xml, g_entry_xml, screen, init);
    }
  else if (strcmp("lobby", string) == 0)
    {
      static GladeXML* 	g_lobby_xml = 0;
      static GladeXML* 	g_table_info_xml = 0;
      static GladeXML* 	g_lobby_tabs_xml = 0;
      static GladeXML* 	g_cashier_button_xml = 0;
      static GladeXML* 	g_clock_xml = 0;
      int init = 0;
      if(!g_lobby_xml) {
        g_lobby_xml = gui_load_widget("lobby_window");
        g_table_info_xml = gui_load_widget("table_info_window");
        g_lobby_tabs_xml = gui_load_widget("lobby_tabs_window");
        g_cashier_button_xml = gui_load_widget("cashier_button_window");
        g_clock_xml = gui_load_widget("clock_window");

        init = 1;
      }

      handle_lobby(g_lobby_xml, g_table_info_xml, g_lobby_tabs_xml, g_cashier_button_xml, g_clock_xml, screen, init);
    }
  else if (strcmp("tournaments", string) == 0)
    {
      static GladeXML* 	g_tournaments_xml = 0;
      static GladeXML* 	g_tournament_info_xml = 0;
      static GladeXML* 	g_lobby_tabs_xml = 0;
      static GladeXML* 	g_cashier_button_xml = 0;
      static GladeXML* 	g_clock_xml = 0;
      int init = 0;
      if(!g_tournaments_xml) {
        g_tournaments_xml = gui_load_widget("tournaments_window");
        g_tournament_info_xml = gui_load_widget("tournament_info_window");
        g_lobby_tabs_xml = gui_load_widget("lobby_tabs_window");
        g_cashier_button_xml = gui_load_widget("cashier_button_window");
        g_clock_xml = gui_load_widget("clock_window");

        init = 1;
      }

      handle_tournaments(g_tournaments_xml, g_tournament_info_xml, g_lobby_tabs_xml, g_cashier_button_xml, g_clock_xml, screen, init);
    }
  else if (strcmp("buy_in", string) == 0)
    {
      static GladeXML*	g_glade_xml = 0;
      int init = 0;
      if(!g_glade_xml) {
        g_glade_xml = gui_load_widget("buy_in_window");
        init = 1;
      }

      handle_buy_in(g_glade_xml, screen, init);
    }
  else if (strcmp("outfit", string) == 0)
    {
      static GladeXML* g_glade_outfit_sex_xml = 0;
      static GladeXML* g_glade_outfit_ok_xml = 0;
      static GladeXML* g_glade_outfit_slots_male_xml = 0;
      static GladeXML* g_glade_outfit_slots_female_xml = 0;
      static GladeXML* g_glade_outfit_params_xml = 0;
      static GladeXML* g_glade_outfit_random_xml = 0;
      int init = 0;
      if(!g_glade_outfit_sex_xml) {
        g_glade_outfit_sex_xml = gui_load_widget("outfit_sex_window");
        g_glade_outfit_ok_xml = gui_load_widget("outfit_ok_window");
        g_glade_outfit_slots_male_xml = gui_load_widget("outfit_slots_male_window");
        g_glade_outfit_params_xml = gui_load_widget("outfit_params_window");
        g_glade_outfit_random_xml = gui_load_widget("outfit_random_window");
        g_glade_outfit_slots_female_xml = gui_load_widget("outfit_slots_female_window");
        init = 1;
      }

      handle_outfit(g_glade_outfit_sex_xml, g_glade_outfit_ok_xml, g_glade_outfit_slots_male_xml, g_glade_outfit_slots_female_xml, g_glade_outfit_params_xml, g_glade_outfit_random_xml, screen, init);
    }
  else if (strcmp("menu", string) == 0)
    {
      static GladeXML*	g_glade_xml = 0;
      int init = 0;
      if(!g_glade_xml) {
        g_glade_xml = gui_load_widget("menu_window");
        init = 1;
      }

      handle_menu(g_glade_xml, screen, init);
    }
  else if (strcmp("quit", string) == 0)
    gtk_main_quit();
  else
    g_warning("unknown packet type: %s", string);

  g_free(string);
  return TRUE;
}

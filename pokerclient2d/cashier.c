/* *
 * Copyright (C) 2004, 2005 Mekensleep
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
 *  Henry Prêcheur <henry at precheur dot org>
 *  Loic Dachary <loic@gnu.org>
 *
 */

#include <string.h>

#include <gtk/gtk.h>
#include <glade/glade.h>
#include "gui.h"
#include "interface_io.h"
#include "dispatcher.h"

static GtkWidget*	s_personal_information_window = 0;
static GtkWidget*	s_account_status_window = 0;
static GtkWidget*	s_exit_cashier_window = 0;
static GtkButton*	s_exit_button = 0;

#define ENTRIES_CNT	2
static GtkWidget*	s_entries[ENTRIES_CNT];
#define LABELS_CNT	6
static GtkWidget*	s_labels[LABELS_CNT];

static position_t	s_personal_information_position;
static position_t	s_account_status_position;
static position_t	s_exit_cashier_position;
static int		s_cashier_shown = 0;

/* static void	close_callback(GtkWidget* w, gpointer data) */
/* { */
/*   g_assert(GTK_IS_LABEL(w)); */
/*   g_assert(GTK_IS_CONTAINER(data)); */

/*   gtk_container_remove(GTK_CONTAINER(data), w); */
/* } */

static void	hide_cashier(void)
{
  gtk_widget_hide(s_personal_information_window);
  gtk_widget_hide(s_account_status_window);
  gtk_widget_hide(s_exit_cashier_window);
}

void	close_cashier(void)
{
  g_message("close user info");
  /*   gtk_container_foreach(GTK_CONTAINER(g_cashier_vbox), close_callback, g_cashier_vbox); */
  set_string("cashier");
  set_string("no");
  flush_io_channel();
}

void	on_exit_cashier_clicked(GtkWidget* widget, gpointer user_data)
{
  (void) widget;
  (void) user_data;

  close_cashier();
}

int	handle_cashier(GladeXML* s_glade_personal_information_xml, GladeXML* s_glade_account_status_xml, GladeXML* s_glade_exit_cashier_xml, GtkLayout* screen, int init)
{
  if (init)
    {
      s_personal_information_window =
        gui_get_widget(s_glade_personal_information_xml,
                       "personal_information_window");
      g_assert(s_personal_information_window);
      set_nil_draw_focus(s_personal_information_window);
      if(screen) gtk_layout_put(screen, s_personal_information_window, 0, 0);
      s_account_status_window =
        gui_get_widget(s_glade_account_status_xml,
                       "account_status_window");
      g_assert(s_account_status_window);
      if(screen) gtk_layout_put(screen, s_account_status_window, 0, 0);
      s_exit_cashier_window = gui_get_widget(s_glade_exit_cashier_xml, "exit_cashier_window");
      g_assert(s_exit_cashier_window);
      if(screen) gtk_layout_put(screen, s_exit_cashier_window, 0, 0);
      s_exit_button = GTK_BUTTON(gui_get_widget(s_glade_exit_cashier_xml, "exit_cashier"));
      g_assert(s_exit_button);


      {
        static const char*	entries[ENTRIES_CNT] =
          {
            "entry_player_id",
            "entry_email",
          };
        int	i;

        for (i = 0; i < ENTRIES_CNT; i++)
          s_entries[i] = gui_get_widget(s_glade_personal_information_xml,
                                        entries[i]);
      }

      {
        static const char*	labels[LABELS_CNT] =
          {
            "play_money_available",
            "play_money_in_game",
            "play_money_total",
            "custom_money_available",
            "custom_money_in_game",
            "custom_money_total"
          };
        int	i;

        for (i = 0; i < LABELS_CNT; i++)
          s_labels[i] = gui_get_widget(s_glade_account_status_xml,
                                       labels[i]);
      }

      GUI_BRANCH(s_glade_exit_cashier_xml, on_exit_cashier_clicked);

      gtk_widget_hide(s_personal_information_window);
      gtk_widget_hide(s_account_status_window);
      gtk_widget_hide(s_exit_cashier_window);
    }

  char* showhide = get_string();

  char*	fields[20];
  char**	pfields = fields;
  int	i = get_int();
  int	fields_cnt = 0;

  if(i > 0) {

    g_message("%d", i);
    while (i-- > 0)
      {
        char*	str = get_string();
        if (fields_cnt < 20)
          fields[fields_cnt++] = str;
      }
  

    for (i = 0; i < ENTRIES_CNT; i++)
      {
        char*	str = *pfields++;
        gtk_entry_set_text(GTK_ENTRY(s_entries[i]), str);
      }

    {
      char* str = *pfields++;
      GtkTextView* address = GTK_TEXT_VIEW(gui_get_widget(s_glade_personal_information_xml, "entry_mailing_address"));
      GtkTextBuffer* buffer = gtk_text_view_get_buffer(address);
      gtk_text_buffer_set_text(buffer, str, -1);
    }

    for (i = 0; i < LABELS_CNT; i++)
      {
        char*	str = *pfields++;
        gtk_label_set_text(GTK_LABEL(s_labels[i]), str);
      }

  }

  if(!strcmp(showhide, "show")) {

    /*
     * calculate windows position
     */
    int	screen_width = gui_width(screen);
    int	screen_height = gui_height(screen);

    /*
     * should be based on the size of the windows ...
     */
    int	top_left_x = (screen_width - 913) / 2;
    int	top_left_y = (screen_height - 450) / 2;
    int	account_status_x = top_left_x + 381;
    int	exit_cashier_y = top_left_y + 320;

    s_personal_information_position.x = top_left_x;
    s_personal_information_position.y = top_left_y;
    s_account_status_position.x = account_status_x;
    s_account_status_position.y = top_left_y;
    s_exit_cashier_position.x = top_left_x;
    s_exit_cashier_position.y = exit_cashier_y;

    {
      char* label = get_string();
      gtk_button_set_label(s_exit_button, label);
      g_free(label);
    }
    
    if ((screen != NULL) || (s_cashier_shown == 0))
    {
      gui_place(s_personal_information_window, &s_personal_information_position, screen);
      gui_place(s_account_status_window, &s_account_status_position, screen);
      gui_place(s_exit_cashier_window, &s_exit_cashier_position, screen);
      s_cashier_shown = 1;
    }
  } else {
    if (screen != NULL)
      {
	hide_cashier();
      }
  }

  g_free(showhide);

  return TRUE;
}

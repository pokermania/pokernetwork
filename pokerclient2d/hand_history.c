/* *
 * Copyright (C) 2004, 2005, 2006 Mekensleep
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
 *
 */

#include <string.h>
#include "gtk/gtk.h"
#include "glade/glade.h"
#include "gui.h"
#include "interface_io.h"
#include "dispatcher.h"
#include <libintl.h>

GtkTextBuffer* s_hand_messages;

static void on_row_activated(GtkTreeView        *treeview,
                             GtkTreePath        *path,
                             GtkTreeViewColumn  *col,
                             gpointer            user_data)
{
  (void) col;
  (void) user_data;

  g_message("row clicked");
  GtkTreeModel*	model;
  GtkTreeIter   iter;

  model = gtk_tree_view_get_model(treeview);

  if (gtk_tree_model_get_iter(model, &iter, path))
    {
      char* hand;

      gtk_tree_model_get(model, &iter, 0, &hand, -1);
      g_message("Double-clicked row contains %s", hand);
      set_string("hand_history");
      set_string("show");
      set_string(hand);
      flush_io_channel();
    }
  else
    g_warning("unable to find active row");
}

static void on_quit_clicked(GtkButton* button, gpointer data)
{
  (void) button;
  (void) data;

  set_string("hand_history");
  set_string("quit");
  flush_io_channel();
}

static void on_next_clicked(GtkButton* button, gpointer data)
{
  (void) button;
  (void) data;

  set_string("hand_history");
  set_string("next");
  flush_io_channel();
}

static void on_previous_clicked(GtkButton* button, gpointer data)
{
  (void) button;
  (void) data;

  set_string("hand_history");
  set_string("previous");
  flush_io_channel();
}

static void on_selection_changed(GtkTreeSelection *treeselection,
                                 gpointer user_data)
{
  (void)user_data;
  GtkTreeModel*	model;
  GtkTreeIter   iter;

  if(gtk_tree_selection_get_selected(treeselection, &model, &iter)) {
      char* hand;

      gtk_tree_model_get(model, &iter, 0, &hand, -1);
      g_message("clicked row contains %s", hand);
      set_string("hand_history");
      set_string("show");
      set_string(hand);
      flush_io_channel();
    }
  else
    g_warning("treeview_selection: unable to find active row");
}

int handle_hand_history(GladeXML* g_glade_xml, GtkLayout* screen, int init)
{
  static GtkWidget*	hand_history_window = NULL;
  static GtkWidget*	previous_widget = NULL;
  static GtkWidget*	next_widget = NULL;

  if(init) {

    textdomain("poker2d");

    hand_history_window = glade_xml_get_widget(g_glade_xml, "hand_history_window");
    g_assert(hand_history_window);
    if(screen) gtk_layout_put(screen, hand_history_window, 0, 0);

    GUI_BRANCH(g_glade_xml, on_quit_clicked);
    GUI_BRANCH(g_glade_xml, on_next_clicked);
    GUI_BRANCH(g_glade_xml, on_previous_clicked);

    GtkTreeView* hand_history = GTK_TREE_VIEW(glade_xml_get_widget(g_glade_xml, "hand_history"));
    g_signal_connect(hand_history, "row-activated", (GCallback)on_row_activated, NULL);
    GtkTreeSelection* selection = gtk_tree_view_get_selection(hand_history);
    g_signal_connect(selection, "changed", (GCallback)on_selection_changed, NULL);

    {
      static GType type_list[1] = { G_TYPE_STRING };
      GtkListStore*	store = gtk_list_store_newv(1, type_list);
      gtk_tree_view_set_model(hand_history, GTK_TREE_MODEL(store));
    }

    {
      GtkTreeViewColumn* column = gtk_tree_view_column_new();
      gtk_tree_view_append_column(hand_history, column);
      GtkCellRenderer*	cell_renderer = gtk_cell_renderer_text_new();
      gtk_tree_view_column_set_title(column, gettext("Show hand") );
      gtk_tree_view_column_pack_start(column, cell_renderer, TRUE);
      gtk_tree_view_column_add_attribute(column, cell_renderer, "text", 0);
    }

    {
      GtkTextView* messages = GTK_TEXT_VIEW(gui_get_widget(g_glade_xml, "hand_messages"));
      s_hand_messages = gtk_text_view_get_buffer(messages);
    }

    previous_widget = glade_xml_get_widget(g_glade_xml, "previous");
    g_assert(previous_widget);

    next_widget = glade_xml_get_widget(g_glade_xml, "next");
    g_assert(next_widget);

  }

  if(!g_glade_xml)
    return FALSE;

  {
    char* tag = get_string();

    if(!strncmp(tag, "hide", 4)) {
      gtk_widget_hide_all(hand_history_window);
    } else if(!strcmp(tag, "show")) {
      int i;
      int start = get_int();
      int count = get_int();
      int total = get_int();
      int hands_count = get_int();
      GtkTreeView*	hand_history = GTK_TREE_VIEW(glade_xml_get_widget(g_glade_xml, "hand_history"));
      GtkListStore* store = GTK_LIST_STORE(gtk_tree_view_get_model(hand_history));
      g_assert(store != 0);
      gtk_list_store_clear(store);

      for(i = 0; i < hands_count; i++) {
        char* hand = get_string();
        GtkTreeIter	iter;
        GValue	value;
        memset(&value, 0, sizeof (GValue));
        gtk_list_store_append(store, &iter);
        g_value_set_string(g_value_init(&value, G_TYPE_STRING), hand);
        gtk_list_store_set_value(store, &iter, 0, &value);
        g_free(hand);
      }

      gui_center(hand_history_window, screen);

      if(start == 0) {
        gtk_widget_set_sensitive(previous_widget, FALSE);
      } else {
        gtk_widget_set_sensitive(previous_widget, TRUE);
      }

      if(start + count >= total) {
	gtk_widget_set_sensitive(next_widget, FALSE);
      } else {
	gtk_widget_set_sensitive(next_widget, TRUE);
      }

      gtk_text_buffer_set_text(s_hand_messages, "", -1);

    } else if(!strcmp(tag, "messages")) {
      int hand_serial = get_int();
      char* messages = get_string();
      (void)hand_serial;
      gtk_text_buffer_set_text(s_hand_messages, messages, -1);
      g_free(messages);
    }

    g_free(tag);
  } 
  
  return TRUE;
}

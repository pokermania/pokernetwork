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
 *  Loic Dachary <loic@gnu.org>
 *  Nicolas Albert <nicolas_albert_85@yahoo.fr>
 *
 */

#include <gtk/gtk.h>
#include <glade/glade.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <assert.h>
#include <libxml2/libxml/xmlreader.h>
#include "gui.h"
#include "interface_io.h"
#include "util.h"
#include "dispatcher.h"

static GtkWidget*	g_history_window = 0;
static GtkWidget*	g_entry_window = 0;
static gboolean		chat_history_visible = FALSE;

GtkStateType current_state;

typedef struct smiley_s
{
  char* text;
  char* filename;
} smiley_t;

static GArray* g_smileys = 0;

static int g_smileys_nb_elem = 0;
static int g_chat_shown = 0;
static int g_chat_history_shown = 0;
/* enum */
/* { */
/*   g_smileys_nb_elem = sizeof(g_smileys)/sizeof(g_smileys[0]) */
/* }; */

static gboolean xml_reader_seek_to_element(xmlTextReaderPtr reader, const char *element)
{
  while ((xmlTextReaderRead(reader) == 1))
    {
      const char* name = ((const char*)xmlTextReaderConstName(reader));
      if ((xmlTextReaderNodeType(reader) == XML_READER_TYPE_ELEMENT) 
          && !strcmp(name, element))
        return TRUE;
    }
  return FALSE;
}


void create_smiley_array(const char *path, const char *filename)
{
  GString *xmlFullPathStr = g_string_new(path);
  g_string_append(xmlFullPathStr, "/");
  g_string_append(xmlFullPathStr, filename);
  char *xmlFullPath = xmlFullPathStr->str;
  xmlTextReaderPtr reader = xmlNewTextReaderFilename(xmlFullPath);
  g_string_free(xmlFullPathStr, TRUE);

  if (reader == 0)
    {
      g_critical("no smiley definition file");
      return;
    }
  GArray* smiley_array = g_array_new(TRUE, TRUE, sizeof(smiley_t));    
  int size = 0;
  if (xml_reader_seek_to_element(reader, "smileys"))
    while(xml_reader_seek_to_element(reader, "smiley"))
      {
        xmlChar* textAttributePtr = xmlTextReaderGetAttribute(reader, (const xmlChar*)"text");
        xmlChar* filenameAttributePtr = xmlTextReaderGetAttribute(reader, (const xmlChar*)"filename");	
        smiley_t smiley;
        smiley.text = g_strdup(textAttributePtr);
        GString *filenameStr = g_string_new(path);
        g_string_append(filenameStr, "/");
        g_string_append(filenameStr, filenameAttributePtr);
        smiley.filename = g_strdup(filenameStr->str);
        g_message("%s\n", smiley.filename);
        g_string_free(filenameStr, TRUE);
        g_array_append_val(smiley_array, smiley);
        xmlFree(textAttributePtr);
        xmlFree(filenameAttributePtr);
        ++size;
      }
  g_smileys = smiley_array;
  g_smileys_nb_elem = size;
}

void destroy_smiley_array(void)
{
  int i;
  for (i = 0; i < g_smileys_nb_elem; ++i)
    {
      smiley_t *smiley = &g_array_index(g_smileys, smiley_t, i);
      g_free(smiley->text);
      g_free(smiley->filename);
    }
  g_array_free(g_smileys, TRUE);
}

int find_smiley(const char *str)
{
  int i;
  for (i = 0; i < g_smileys_nb_elem; ++i)
    {
      const smiley_t *smiley = &g_array_index(g_smileys, smiley_t, i);
      const char *text = smiley->text;
      int text_len = strlen(text);
      if (!strncmp(str, text, text_len))
        return i;
    }
  return -1;
}

void	on_history_clicked(GtkWidget *widget, gpointer user_data)
{
  (void) user_data;
  (void) widget;
  chat_history_visible = !chat_history_visible;
  set_string("chat");
  set_string("history");
  set_string(chat_history_visible ? "yes" : "no");
  flush_io_channel();
  current_state = chat_history_visible ? GTK_STATE_ACTIVE : GTK_STATE_NORMAL;
  gtk_widget_set_state(widget,current_state);
}

void	on_history_focus(GtkWidget *widget, gpointer user_data)
{
  (void) user_data;
  (void) widget;
  gtk_widget_grab_focus(g_entry_window);
}

void	on_history_state_changed(GtkWidget *widget, gpointer user_data)
{
  (void) user_data;
  (void) widget;
	gtk_widget_set_state(widget,current_state);
}

void	on_chat_done(GtkWidget *widget, gpointer user_data)
{
  (void) user_data;
  const gchar* line = gtk_entry_get_text(GTK_ENTRY(widget));
  if(strlen(line) > 0) {
    set_string("chat");
    set_string("line");
    set_string(line);
    gtk_entry_set_text(GTK_ENTRY(widget), "");
    flush_io_channel();
  }
}

int	handle_chat(GladeXML* g_history_xml, GladeXML* 	g_entry_xml, GtkLayout* screen, int init)
{
	char*	tag = get_string();

	if (init)
		{
			g_history_window = glade_xml_get_widget(g_history_xml,
																							"chat_history_window");
			g_assert(g_history_window);
			set_nil_draw_focus(g_history_window);
			if(screen) gtk_layout_put(screen, g_history_window, 0, 0);
			g_entry_window = glade_xml_get_widget(g_entry_xml,
																						"chat_entry_window");
			g_assert(g_entry_window);
			if(screen) gtk_layout_put(screen, g_entry_window, 0, 0);

			GUI_BRANCH(g_entry_xml, on_history_clicked);
			GUI_BRANCH(g_entry_xml, on_history_state_changed);
			GUI_BRANCH(g_entry_xml, on_history_focus);
			GUI_BRANCH(g_entry_xml, on_chat_done);

			gtk_widget_hide_all(GTK_WIDGET(g_entry_window)); // chat bar
			// must be
			// shown
			// explicitely
			// with a
			// "show"
			// packet
			{
				GtkWidget*	button = glade_xml_get_widget(g_entry_xml, "history_button");
				g_assert(button);
				gtk_widget_set_state(button,GTK_STATE_NORMAL);
				current_state = GTK_WIDGET_STATE(button);
			}
		}

  if(!strcmp(tag, "show"))
    {
			if ((screen != NULL) || (g_chat_shown == 0))
				{
					int	screen_width = gui_width(screen);
					int	screen_height = gui_height(screen);
					int	chat_entry_window_height;

					{
						static position_t position;
						gtk_widget_show_all(g_entry_window);
						gtk_widget_get_size_request(g_entry_window, &position.x, &position.y);
						chat_entry_window_height = position.y;
						position.x = (screen_width - position.x) / 2;
						position.y = screen_height - position.y;
						g_message("chat: position x = %d, y = %d", position.x, position.y);
						gui_place(g_entry_window, &position, screen);
					}
					{
						static position_t position;
						gtk_widget_show_all(g_history_window);
						gtk_widget_get_size_request(g_history_window, &position.x, &position.y);
						position.x = (screen_width - position.x) / 2;
						position.y = (screen_height - (position.y + chat_entry_window_height));
						gui_place(g_history_window,&position, screen);
					}
					/* reset previously inserted text */
					GtkTextView* history = GTK_TEXT_VIEW(glade_xml_get_widget(g_history_xml,
																																		"history"));
					GtkTextBuffer* buffer = gtk_text_view_get_buffer(history);
					gtk_text_buffer_set_text(buffer, "", sizeof (""));
					g_chat_shown = 1;
				}
    }
  else if(!strcmp(tag, "hide"))
    {
			if (screen != NULL) {
				gtk_widget_hide_all(g_entry_window); 
				gtk_widget_hide_all(g_history_window); 
			}
    }
  else if(!strcmp(tag, "history"))
    {
      char *action = get_string();
      if(!strcmp(action, "show")) {
				if ((screen != NULL) || (g_chat_history_shown == 0)) {
					gtk_widget_show_all(g_history_window);
					g_chat_history_shown = 1;
				}
      } else if(!strcmp(action, "hide")) {
				if (screen != NULL)
					gtk_widget_hide_all(g_history_window); 
      } else {
        g_critical("chat history: unknow action %s ignored", action);
      }
      g_free(action);
    }
  else if(!strcmp(tag, "line"))
    {
      
      char*	line = get_string();
      GtkTextView* history = GTK_TEXT_VIEW(glade_xml_get_widget(g_history_xml,
                                                                "history"));
      GtkTextBuffer* buffer = gtk_text_view_get_buffer(history);
      
      GtkTextIter end_iter;
      gtk_text_buffer_get_end_iter(buffer, &end_iter);

      {
        char *str = line;
        while(*str)
          {
            int index = find_smiley(str);
            if (index >= 0)
              {
                GError* error = 0;
                const smiley_t *smiley = &g_array_index(g_smileys, smiley_t, index);
                const char *text = smiley->text;
                const char *filename = smiley->filename;
                GdkPixbuf* pixbuf = gdk_pixbuf_new_from_file(filename, &error);
                gtk_text_buffer_insert_pixbuf(buffer, &end_iter, pixbuf);
                str += strlen(text);
              }
            else
              {
                gtk_text_buffer_insert(buffer, &end_iter, str, 1);
                str++;
              }
          }
      }
      gtk_text_buffer_get_end_iter(buffer, &end_iter);
      gtk_text_view_scroll_to_iter(history, &end_iter,
                                   0.1,
                                   FALSE,
                                   0.0,
                                   0.0);
      g_free(line);
    }
  
  g_free(tag);

  return TRUE;
}

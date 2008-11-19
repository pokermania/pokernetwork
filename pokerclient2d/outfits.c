/* *
 * Copyright (C) 2004, 2005, 2006 Mekensleep <licensing@mekensleep.com>
 *                                24 rue vieille du temple, 75004 Paris
 *
 * This software's license gives you freedom; you can copy, convey,
 * propogate, redistribute and/or modify this program under the terms of
 * the GNU Affero General Public License (AGPL) as published by the Free
 * Software Foundation (FSF), either version 3 of the License, or (at your
 * option) any later version of the AGPL published by the FSF.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero
 * General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program in a file in the toplevel directory called
 * "AGPLv3".  If not, see <http://www.gnu.org/licenses/>.
 *
 * Authors:
 *  Loic Dachary <loic@gnu.org>
 *  Cedric Pinson <cpinson@freesheep.org>
 */

#include <assert.h>
#include <string.h>
#include <math.h>
#include <gtk/gtk.h>
#include <glade/glade.h>
#include "gui.h"
#include "interface_io.h"
#include "dispatcher.h"

extern char*	g_data_dir;

static GtkWidget* g_outfit_sex_window;
static GtkWidget* g_outfit_ok_window;
static GtkWidget* g_outfit_slots_male_window;
static GtkWidget* g_outfit_slots_female_window;
static GtkWidget* g_outfit_params_window;
static GtkWidget* g_outfit_random_window;

struct outfit_params {
  char name[32];
  int has_colors;
  char colors[30][10];
  GdkRectangle rectangle;
  int has_filename;
  char filename[256];
  GdkGC* gc;
  GtkImage* preview;
  GtkAdjustment* adjustment;
};

struct outfit_slider_slot {
  GtkAdjustment* adjustment;
};

static struct outfit_slider_slot slider_slot_user_data;
static struct outfit_params params_user_data[5];
static gulong params_handlers[5];
static int    g_outfit_shown = 0;

static void on_ok_clicked(GtkButton *button, gpointer user_data)
{
  (void) button;
  (void) user_data;
  set_string("outfit");
  set_string("ok");
  flush_io_channel();
}

static void on_random_clicked(GtkToggleButton *button, gpointer user_data)
{
  (void) button;
  (void) user_data;
  set_string("outfit");
  set_string("random");
  flush_io_channel();
}

static void	on_sex_toggled(GtkWidget *widget, gpointer user_data)
{
  (void) user_data;

  g_message("on_sex_toggled");
  if(gtk_toggle_button_get_active(GTK_TOGGLE_BUTTON(widget))) {
    set_string("outfit");
    set_string("sex");
    set_string(gtk_widget_get_name(widget));
    flush_io_channel();
  }
}

static int slots_disable = 0;

static void	on_outfit_toggled(GtkWidget *widget, gpointer user_data)
{
  (void) user_data;

  if(slots_disable == 0) {
    set_string("outfit");
    set_string("slot_type");
    const char* name = gtk_widget_get_name(widget);
    set_string(name);
    if(gtk_toggle_button_get_active(GTK_TOGGLE_BUTTON(widget))) {
      set_string("on");
    } else {
      set_string("off");
    }
    flush_io_channel();
  }
}

static void param_update_preview(struct outfit_params* params, int value)
{
  GtkImage* preview = params->preview;
  GdkWindow* window = GTK_WIDGET(preview)->window;
  GtkAllocation allocation = GTK_WIDGET(preview)->allocation;

  if(params->gc == NULL)
    params->gc = gdk_gc_new(window);

  if(params->has_colors) {
    GdkRectangle rectangle = params->rectangle;
    rectangle.x += allocation.x;
    rectangle.y += allocation.y;
    GdkRegion* region = gdk_region_rectangle(&rectangle);
    gdk_window_invalidate_region(window, region, FALSE);
    gdk_region_destroy(region);
  } else if(params->has_filename) {
    char image_name[1024];
    sprintf(image_name, params->filename, g_data_dir, value);
    gtk_image_set_from_file(preview, image_name);
  }
}

static void on_param_value_changed(GtkAdjustment *adjustment, gpointer user_data)
{
  struct outfit_params* params = (struct outfit_params*)user_data;
  /*
   * Output new value
   */
  int value = (int)(gtk_adjustment_get_value(adjustment));

  set_string("outfit");
  set_string("parameter");
  set_string(params->name);
  set_int((int)value);
  flush_io_channel();
  param_update_preview(params, value);
}

static gboolean on_param_expose_event(GtkImage *preview, GdkEventExpose *event, gpointer user_data)
{
  (void)event;
  struct outfit_params* params = (struct outfit_params*)user_data;

  GdkWindow* window = GTK_WIDGET(preview)->window;
  GtkAllocation allocation = GTK_WIDGET(preview)->allocation;
  if(params->gc == NULL)
    params->gc = gdk_gc_new(window);

  if(params->has_colors) {
    GdkColor color;
    GdkRectangle rectangle = params->rectangle;
    int current = (int)gtk_adjustment_get_value(params->adjustment);
    rectangle.x += allocation.x;
    rectangle.y += allocation.y;
    g_message("on_param_expose --- %s\n",params->name);
    g_message("on_param_expose --- current %d\n",current);
    if(!gdk_color_parse(params->colors[current], &color)) {
      g_message("param_expose_event color conversion failed for %d/%s", current, params->colors[current]);
      return FALSE;
    }
    gdk_gc_set_rgb_fg_color(params->gc, &color);
    gdk_draw_rectangle(window, params->gc, TRUE, rectangle.x, rectangle.y, rectangle.width, rectangle.height);
  }
  return FALSE;
}

static void on_arrow_clicked(GtkAdjustment* adjustment, gdouble increment)
{
  gdouble upper;
  gdouble value;
  g_object_get(GTK_OBJECT(adjustment),
               "upper", &upper,
               "value", &value,
               NULL);
  /*
   * check that value is in the range [0,upper] and wrap around
   */
  if((value + increment) < 0.0) {
    value = upper;
    g_message("ARROW CLICKED wrap %f", value);
  } else if((value + increment) - upper > 0.0) {
    value = 0.0;
    g_message("ARROW CLICKED wrap 0");
  } else {
    g_message("ARROW CLICKED value changed %f\n", value + increment);
    value += increment;
  }

  gtk_adjustment_set_value(adjustment, value);
}

static void on_slot_left_clicked(GtkToggleButton *button, gpointer user_data)
{
  struct outfit_slider_slot* param = (struct outfit_slider_slot*)user_data;
  (void) button;

  /*   g_message("SLIDER SLOT left clicked\n"); */

  on_arrow_clicked(param->adjustment, -1.);
}

static void on_slot_right_clicked(GtkToggleButton *button, gpointer user_data)
{
  struct outfit_slider_slot* param = (struct outfit_slider_slot*)user_data;
  (void) button;

  /*   g_message("SLIDER SLOT right clicked\n"); */

  on_arrow_clicked(param->adjustment, 1.);
}

static void on_param_left_clicked(GtkToggleButton *button, gpointer user_data)
{
  struct outfit_params* param = (struct outfit_params*)user_data;
  (void) button;

  on_arrow_clicked(param->adjustment, -1.);
}

static void on_param_right_clicked(GtkToggleButton *button, gpointer user_data)
{
  struct outfit_params* param = (struct outfit_params*)user_data;
  (void) button;

  on_arrow_clicked(param->adjustment, 1.);
}

static void on_slot_value_changed(GtkAdjustment* adjustment, gpointer user_data)
{
  (void)user_data;
  g_message("SLOT VALUE value changed\n");

  gdouble value = gtk_adjustment_get_value(GTK_ADJUSTMENT(adjustment));

  set_string("outfit");
  set_string("slot");
  set_int((int)value);
  flush_io_channel();
}

int handle_outfit(GladeXML* g_glade_outfit_sex_xml, GladeXML* g_glade_outfit_ok_xml, GladeXML* g_glade_outfit_slots_male_xml, GladeXML* g_glade_outfit_slots_female_xml, GladeXML* g_glade_outfit_params_xml, GladeXML* g_glade_outfit_random_xml, GtkLayout* screen, int init)
{
  if (init) {
    /*
     * Sex
     */
    g_assert(g_glade_outfit_sex_xml);
    g_outfit_sex_window = glade_xml_get_widget(g_glade_outfit_sex_xml, "outfit_sex_window");
    g_assert(g_outfit_sex_window);
    set_nil_draw_focus(g_outfit_sex_window);
    if(screen) gtk_layout_put(screen, g_outfit_sex_window, 0, 0);
    GUI_BRANCH(g_glade_outfit_sex_xml, on_sex_toggled);
    gtk_widget_hide_all(g_outfit_sex_window);

    /*
     * Ok
     */
    g_assert(g_glade_outfit_ok_xml);
    g_outfit_ok_window = glade_xml_get_widget(g_glade_outfit_ok_xml, "outfit_ok_window");
    g_assert(g_outfit_ok_window);
    if(screen) gtk_layout_put(screen, g_outfit_ok_window, 0, 0);
    GUI_BRANCH(g_glade_outfit_ok_xml, on_ok_clicked);
    gtk_widget_hide_all(g_outfit_ok_window);

    /*
     * Random
     */
    g_assert(g_glade_outfit_random_xml);
    g_outfit_random_window = glade_xml_get_widget(g_glade_outfit_random_xml, "outfit_random_window");
    g_assert(g_outfit_random_window);
    if(screen) gtk_layout_put(screen, g_outfit_random_window, 0, 0);
    GUI_BRANCH(g_glade_outfit_random_xml, on_random_clicked);
    gtk_widget_hide_all(g_outfit_random_window);

    /*
     * Parameters
     */
    if (!g_glade_outfit_params_xml)
      return FALSE;
    g_outfit_params_window = glade_xml_get_widget(g_glade_outfit_params_xml, "outfit_params_window");
    if(screen) gtk_layout_put(screen, g_outfit_params_window, 0, 0);
    {
      GtkObject* left = GTK_OBJECT(glade_xml_get_widget(g_glade_outfit_params_xml, "slot_left"));
      g_assert(left);
      g_signal_connect(left, "pressed", (GtkSignalFunc)on_slot_left_clicked, (gpointer)&slider_slot_user_data);
      GtkObject* right = GTK_OBJECT(glade_xml_get_widget(g_glade_outfit_params_xml, "slot_right"));
      g_assert(right);
      g_signal_connect(right, "pressed", (GtkSignalFunc)on_slot_right_clicked, (gpointer)&slider_slot_user_data);
      slider_slot_user_data.adjustment = GTK_ADJUSTMENT(gtk_adjustment_new(.0, .0, 1., 1., 1., 1.));
      params_handlers[0] = g_signal_connect(GTK_OBJECT(slider_slot_user_data.adjustment), "value_changed", (GtkSignalFunc)on_slot_value_changed, (gpointer)&slider_slot_user_data);
    }
    int i;
    for(i = 1; i <= 4; i++) {
      char widget_name[32];
      sprintf(widget_name, "param%d_left", i);
      GtkObject* left = GTK_OBJECT(glade_xml_get_widget(g_glade_outfit_params_xml, widget_name));
      g_assert(left);
      g_signal_connect(left, "pressed", (GtkSignalFunc)on_param_left_clicked, (gpointer)&params_user_data[i]);
      sprintf(widget_name, "param%d_right", i);
      GtkObject* right = GTK_OBJECT(glade_xml_get_widget(g_glade_outfit_params_xml, widget_name));
      g_assert(right);
      g_signal_connect(right, "pressed", (GtkSignalFunc)on_param_right_clicked, (gpointer)&params_user_data[i]);
      params_user_data[i].adjustment = GTK_ADJUSTMENT(gtk_adjustment_new(.0, .0, .1, 1., 1., 1.));
      params_handlers[i] = g_signal_connect(GTK_OBJECT(params_user_data[i].adjustment), "value_changed", (GtkSignalFunc)on_param_value_changed, (gpointer)&params_user_data[i]);

      sprintf(widget_name, "param%d_image", i);
      GtkObject* object = GTK_OBJECT(glade_xml_get_widget(g_glade_outfit_params_xml, widget_name));
      g_assert(object);
      g_signal_connect(object, "expose_event", (GtkSignalFunc)on_param_expose_event, (gpointer)&params_user_data[i]);
    }
    gtk_widget_hide_all(g_outfit_params_window);

    /*
     * Slots (head, torso...)
     */
    g_assert(g_glade_outfit_slots_male_xml);
    g_outfit_slots_male_window = glade_xml_get_widget(g_glade_outfit_slots_male_xml, "outfit_slots_male_window");
    g_assert(g_outfit_slots_male_window);
    if(screen) gtk_layout_put(screen, g_outfit_slots_male_window, 0, 0);
    GUI_BRANCH(g_glade_outfit_slots_male_xml, on_outfit_toggled);
    gtk_widget_hide_all(g_outfit_slots_male_window);
#if 0
    {
      GtkStyle* style = gtk_widget_get_style(g_outfit_slots_male_window);
      g_assert(style);
      GTK_STYLE_GET_CLASS(style)->draw_focus = nil_draw_focus;
    }
#endif
    g_assert(g_glade_outfit_slots_female_xml);
    g_outfit_slots_female_window = glade_xml_get_widget(g_glade_outfit_slots_female_xml, "outfit_slots_female_window");
    g_assert(g_outfit_slots_female_window);
    if(screen) gtk_layout_put(screen, g_outfit_slots_female_window, 0, 0);
    GUI_BRANCH(g_glade_outfit_slots_female_xml, on_outfit_toggled);
    gtk_widget_hide_all(g_outfit_slots_female_window);

  }

  {
    char* tag = get_string();

    if(!strcmp(tag, "show")) {
      int	window_width, window_height;
      int	screen_width = gui_width(screen);
      int	screen_height = gui_height(screen);
      int center_x = screen_width / 2;
      int center_y = screen_height / 2;
      
      if (screen != NULL || g_outfit_shown == 0) {
	{
	  static position_t position;
	  gtk_widget_get_size_request(g_outfit_sex_window, &window_width, &window_height);
	  position.x = center_x - 5;
	  position.y = center_y - 336;
	  gui_place(g_outfit_sex_window, &position, screen);
	  gtk_widget_show_all(g_outfit_sex_window);
	}
	{
	  static position_t position;
	  gtk_widget_get_size_request(g_outfit_ok_window, &window_width, &window_height);
	  position.x = center_x + 414;
	  position.y = center_y + 310;
	  gui_place(g_outfit_ok_window, &position, screen);
	  gtk_widget_show_all(g_outfit_ok_window);
	}
	{
	  static position_t position;
	  gtk_widget_get_size_request(g_outfit_random_window, &window_width, &window_height);
	  position.x = center_x - 300;
	  position.y = center_y + 325;
	  gui_place(g_outfit_random_window, &position, screen);
	  gtk_widget_show_all(g_outfit_random_window);
	}
	{
	  static position_t position;
	  gtk_widget_get_size_request(g_outfit_params_window, &window_width, &window_height);
	  position.x = center_x + 50;
	  position.y = center_y + 25;
	  gui_place(g_outfit_params_window, &position, screen);
	  gtk_widget_show_all(g_outfit_params_window);
	}
	g_outfit_shown = 1;
      }
    } else if(!strcmp(tag, "hide")) {

      if (screen != NULL) {
	gtk_widget_hide_all(g_outfit_sex_window);
	gtk_widget_hide_all(g_outfit_ok_window);
	gtk_widget_hide_all(g_outfit_random_window);
	gtk_widget_hide_all(g_outfit_params_window);
	gtk_widget_hide_all(g_outfit_slots_male_window);
	gtk_widget_hide_all(g_outfit_slots_female_window);
      }

    } else if(!strcmp(tag, "set")) {
      char* sex;
      char widget_name[32];
      /*
       * Sex
       */
      {
        int	window_width, window_height;
        int	screen_width = gui_width(screen);
        int	screen_height = gui_height(screen);
        int center_x = screen_width / 2;
        int center_y = screen_height / 2;

        sex = get_string();
        GtkToggleButton* sex_widget = GTK_TOGGLE_BUTTON(glade_xml_get_widget(g_glade_outfit_sex_xml, sex));
        g_assert(sex_widget);
        gtk_toggle_button_set_active(sex_widget, TRUE);
        if(!strcmp(sex, "female")) {
          static position_t position;
          gtk_widget_get_size_request(g_outfit_slots_female_window, &window_width, &window_height);
          position.x = center_x + 50;
          position.y = center_y - 246;
          gui_place(g_outfit_slots_female_window, &position, screen);
          gtk_widget_show_all(g_outfit_slots_female_window);
          gtk_widget_hide_all(g_outfit_slots_male_window);
        } else {
          static position_t position;
          gtk_widget_get_size_request(g_outfit_slots_male_window, &window_width, &window_height);
          position.x = center_x + 50;
          position.y = center_y - 246;
          gui_place(g_outfit_slots_male_window, &position, screen);
          gtk_widget_show_all(g_outfit_slots_male_window);
          gtk_widget_hide_all(g_outfit_slots_female_window);
        }
      }
      /*
       * Slot type
       */
      int slot = get_int();
      int i;
      slots_disable = 1;
      {
        sprintf(widget_name, "outfit%d", slot);
        GtkToggleButton* slot_widget;
        if(!strcmp(sex, "male")) {
          slot_widget = GTK_TOGGLE_BUTTON(glade_xml_get_widget(g_glade_outfit_slots_male_xml, widget_name));
        } else {
          slot_widget = GTK_TOGGLE_BUTTON(glade_xml_get_widget(g_glade_outfit_slots_female_xml, widget_name));
        }
        g_assert(slot_widget);

        gtk_toggle_button_set_active(slot_widget, TRUE);

        GtkImage* slot_thumb = GTK_IMAGE(glade_xml_get_widget(g_glade_outfit_params_xml, "slot_image"));
        g_assert(slot_thumb);
        char image_name[1024];
        sprintf(image_name, "%s/parameters/param1_slot%d_%s.png", g_data_dir, slot, sex);
        gtk_image_set_from_file(slot_thumb, image_name);
      }
      slots_disable = 0;

      /*
       * Slot value
       */

      int slot_cant_be_displayed = 0;
      GtkWidget* container = GTK_WIDGET(glade_xml_get_widget(g_glade_outfit_params_xml, "slot"));
      g_assert(container);
      {
        char* title = get_string();
        int min_value = get_int();
        int max_value = get_int();
        int value = get_int();

        if (max_value-1 > min_value) {
          gtk_widget_set_child_visible(container, TRUE);

          GtkLabel* label = GTK_LABEL(glade_xml_get_widget(g_glade_outfit_params_xml, "slot_label"));
          g_assert(label);
          gtk_label_set_text(label, gettext(title) );

          GtkAdjustment* adjustment = slider_slot_user_data.adjustment;

          g_message("SLIDER SLOT value change: %d => %d, max_value = %d\n", (int)gtk_adjustment_get_value(adjustment), value, max_value);
          g_signal_handler_block((gpointer)adjustment, params_handlers[0]);
          gtk_adjustment_set_value(adjustment, value);
          g_object_set(GTK_OBJECT(adjustment),
                       "lower", (gdouble)min_value,
                       "upper", (gdouble)(max_value - 1),
                       NULL);
          g_signal_handler_unblock((gpointer)adjustment, params_handlers[0]);
        } else {
          gtk_widget_set_child_visible(container, FALSE);
          slot_cant_be_displayed = 1;
        }

        g_free(title);
      }
      /*
       * Slot parameters
       */
      int params_count = get_int();
      for(i = 1; i <= 4; i++) {
        sprintf(widget_name, "param%d", i);
        GtkWidget* container = GTK_WIDGET(glade_xml_get_widget(g_glade_outfit_params_xml, widget_name));
        g_assert(container);
        if(i <= params_count) {
          gtk_widget_set_child_visible(container, TRUE);
          char* title = get_string();
          char* tag = get_string();
          int min_value = get_int();
          int max_value = get_int();
          int value = get_int();


          /*
           * Preview
           */
          {
            char* preview_type = get_string();
            char image_name[1024];

            sprintf(widget_name, "param%d_image", i);
            GtkImage* image = GTK_IMAGE(glade_xml_get_widget(g_glade_outfit_params_xml, widget_name));
            params_user_data[i].preview = image;
            params_user_data[i].gc = NULL;

            if(!strcmp(preview_type, "basecolor") || !strcmp(preview_type, "detailcolor")) {
              int preview_count = get_int();
              int j;
              params_user_data[i].has_colors = TRUE;
              for(j = 0; j < preview_count; j++) {
                char* info = get_string();
                strcpy(params_user_data[i].colors[j], info);
                g_free(info);
              }
              if(!strcmp(preview_type, "basecolor")) {
                sprintf(image_name, "%s/parameters/%s.png", g_data_dir, preview_type);
                gtk_image_set_from_file(image, image_name);
                GdkRectangle r;
                r.x = 14;
                r.y = 15;
                r.width = 30;
                r.height = 30;
                params_user_data[i].rectangle = r;
              } else if(!strcmp(preview_type, "detailcolor")) {
                sprintf(image_name, "%s/parameters/%s.png", g_data_dir, preview_type);
                gtk_image_set_from_file(image, image_name);
                GdkRectangle r;
                r.x = 20;
                r.y = 20;
                r.width = 18;
                r.height = 18;
                params_user_data[i].rectangle = r;
              } else {
                g_assert("unknown type" == 0);
              }
            } else if(!strcmp(preview_type, "file")) {
              get_int();
              params_user_data[i].has_filename = TRUE;
              char* info = get_string();
              strcpy(params_user_data[i].filename, "%s/parameters/");
              strcat(params_user_data[i].filename, info);
              g_free(info);
            }

            g_free(preview_type);
          }
          
          sprintf(widget_name, "param%d_label", i);
          GtkLabel* label = GTK_LABEL(glade_xml_get_widget(g_glade_outfit_params_xml, widget_name));
          g_assert(label);
          gtk_label_set_text(label, gettext(title) );

          sprintf(widget_name, "param%d_slider", i);
          GtkAdjustment* adjustment = params_user_data[i].adjustment;

          strcpy(params_user_data[i].name, tag);

          g_message("SLIDER PARAM value change: %d => %d, max_value %d", (int)gtk_adjustment_get_value(adjustment), value, max_value);
          g_signal_handler_block((gpointer)adjustment, params_handlers[i]);
          g_object_set(GTK_OBJECT(adjustment),
                       "lower", (gdouble)min_value,
                       "upper", (gdouble)(max_value - 1),
                       NULL);
          gtk_adjustment_set_value(adjustment, value);
          param_update_preview(&params_user_data[i], value);
          g_signal_handler_unblock((gpointer)adjustment, params_handlers[i]);

          g_free(tag);
          g_free(title);
        } else {
          gtk_widget_set_child_visible(container, FALSE);
        }
      }

      g_free(sex);
    }

    g_free(tag);
  }
  return TRUE;
}

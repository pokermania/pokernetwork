/* *
 * Copyright (C) 2004, 2005, 2006 Mekensleep <licensing@mekensleep.com>
 *                                24 rue vieille du temple, 75004 Paris
 *
 * This software's license gives you freedom; you can copy, convey,
 * propagate, redistribute and/or modify this program under the terms of
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
 *  Loic Dachary <loic@dachary.org>
 *
 */

#include "util.h"

static gboolean is_numeric_string(const gchar *str, gint len)
{
  while(len--)
    {
      char c = *str;
      if (!(c >= '0' && c <= '9'))
	return FALSE;	
    }
  return TRUE;
}

void entry_numeric_constraint(GtkEditable *editable,
			      gchar *new_text,
			      gint new_text_length,
			      gint *position,
			      gpointer user_data)
{
  (void) editable;
  (void) new_text;
  (void) new_text_length;
  (void) position;
  (void) user_data;
  if (!is_numeric_string(new_text, new_text_length))
    g_signal_stop_emission(editable, g_signal_lookup("insert_text", g_type_from_name("GtkEditable")), 0);
}

static void noLog(const gchar *log_domain,
		  GLogLevelFlags log_level,
		  const gchar *message,
		  gpointer user_data) {
  (void) log_domain;
  (void) log_level;
  (void) message;
  (void) user_data;
}

void set_verbose(int verbose) {
  if(verbose == 0) {
    g_log_set_handler(NULL,
		      (GLogLevelFlags)(G_LOG_LEVEL_WARNING |
				       G_LOG_LEVEL_MESSAGE |
				       G_LOG_LEVEL_INFO |
				       G_LOG_LEVEL_DEBUG),
		      noLog, NULL);
  } else if(verbose == 1) {
    g_log_set_handler(NULL,
		      (GLogLevelFlags)(G_LOG_LEVEL_INFO |
				       G_LOG_LEVEL_DEBUG),
		      noLog, NULL);
    g_log_set_handler(NULL,
		      (GLogLevelFlags)(G_LOG_LEVEL_WARNING |
				       G_LOG_LEVEL_MESSAGE),
		      g_log_default_handler, NULL);
  } else if(verbose == 2) {
    g_log_set_handler(NULL,
		      (GLogLevelFlags)(G_LOG_LEVEL_DEBUG),
		      noLog, NULL);
    g_log_set_handler(NULL,
		      (GLogLevelFlags)(G_LOG_LEVEL_INFO |
				       G_LOG_LEVEL_WARNING |
				       G_LOG_LEVEL_MESSAGE),
		      g_log_default_handler, NULL);
  } else {
    g_log_set_handler(NULL,
		      (GLogLevelFlags)(G_LOG_LEVEL_WARNING |
				       G_LOG_LEVEL_MESSAGE |
				       G_LOG_LEVEL_INFO |
				       G_LOG_LEVEL_DEBUG),
		      g_log_default_handler, NULL);
  }
}

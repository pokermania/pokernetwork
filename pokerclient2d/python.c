/*
 *
 * Copyright (C) 200xo5 Mekensleep
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

#ifdef _DEBUG // for Windows python23_d.lib is not in distribution... ugly but works
 #undef _DEBUG
 #include <Python.h>
 #define _DEBUG
#else
 #include <Python.h>
#endif

#include <glib.h>
#include <gtk/gtk.h>

#include "util.h"
#include "gui.h"
#include "dispatcher.h"

/*
 * From python-gtk2-2.6.2/gobject/pygobject.h
 */
typedef struct {
    PyObject_HEAD
    GObject *obj;
  /* ... */
} PyGObject;

#define pygobject_get(v) (((PyGObject *)(v))->obj)

static PyObject* in_stream = 0;
static PyObject* out_stream = 0;

static PyObject* callback = NULL;

char* g_data_dir = NULL;

char*	get_string(void) {
  char* result = NULL;
  if(PyList_Size(in_stream) > 0) {
    PyObject* item = PyList_GetItem(in_stream, 0);
    if(!PyString_Check(item))
      g_error("get_string: not a string");
    result = g_strdup(PyString_AsString(item));
    if(PyList_SetSlice(in_stream, 0, 1, NULL)) {
      g_free(result);
      return NULL;
    }
  }
  return result;
}
int	get_int(void) {
  char* str_result = get_string();
  g_assert(str_result);
  int result = atoi(str_result);
  g_free(str_result);
  return result;
}

void	set_string(const char* str) {
  PyObject* item = PyString_FromString(str);
  PyList_Append(out_stream, item);
  Py_DECREF(item);
}

void	set_int(int i) {
  char* tmp = g_malloc(16);
  snprintf(tmp, 16, "%d", i);
  set_string(tmp);
}

void flush_io_channel(void) {
  g_assert(callback);
  PyObject* tuple = PyList_AsTuple(out_stream);
  g_assert(tuple);
  g_assert(PyList_SetSlice(out_stream, 0, PyList_Size(out_stream), NULL) == 0);
  {
    PyGILState_STATE state = PyGILState_Ensure();
    PyObject* result = PyObject_Call(callback, tuple, NULL);
    PyGILState_Release(state);
    if(result) { Py_DECREF(result); }
  }
  Py_DECREF(tuple);
}

int	init_interface_io(const char* address) {
  (void)address;
  return 1;
}

static char doc_command[] = 
"";

static PyObject*
command(PyObject* self, PyObject *args)
{
  GtkLayout* screen = 0;

  (void)self;
  if(!PyTuple_Check(args)) {
    PyErr_SetString(PyExc_TypeError, "argument list is not a tuple");
    return NULL;
  }
  
  int args_size = PyTuple_Size(args);
  if(args_size < 1) {
    PyErr_SetString(PyExc_RuntimeError, "command argument list must begin with a GtkLayout object");
    return NULL;
  }
      
  {
    PyObject* item = PyTuple_GetItem(args, 0);
    screen = GTK_LAYOUT(pygobject_get(item));
  }

  {
    int i;
    for(i = 1; i < args_size; i++) {
      if(!PyString_Check(PyTuple_GetItem(args, i))) {
        PyErr_Format(PyExc_TypeError, "command: list element %d is not a string", i);
        return NULL;
      }
    }
    {
      g_assert(PyList_Size(in_stream) == 0);
      if(PyList_SetSlice(in_stream, 0, 0, args))
        return NULL;
      if(PyList_SetSlice(in_stream, 0, 1, NULL))
        return NULL;
    }
  }

  while(PyList_Size(in_stream) > 0)
    dispatcher(screen);

  Py_INCREF(Py_None);
  return Py_None;
}

static char doc_uninit[] = 
"";

static PyObject*
uninit(PyObject* self, PyObject *args)
{
  (void)self;
  (void)args;
  if(in_stream) { Py_DECREF(in_stream); in_stream = 0; }
  if(out_stream) { Py_DECREF(out_stream); out_stream = 0; }
  if(callback) { Py_DECREF(callback); callback = 0; }
  Py_INCREF(Py_None);
  return Py_None;
}

static char doc_init[] = 
"";

static PyObject*
init(PyObject* self, PyObject *args, PyObject *keywds)
{
  char* glade = NULL;
  char* gtkrc = NULL;
  int verbose = 0;
  (void)self;

  static char *kwlist[] = {"callback", "glade", "datadir", "gtkrc", "verbose", NULL};

  if (!PyArg_ParseTupleAndKeywords(args, keywds, "Os|ssi", kwlist, 
                                   &callback, &glade, &g_data_dir, &gtkrc, &verbose))
    return NULL; 

  if(!PyCallable_Check(callback)) {
    PyErr_SetString(PyExc_TypeError, "callback must be a callable");
    return NULL;
  }
  Py_INCREF(callback);
  
  in_stream = PyList_New(0);
  out_stream = PyList_New(0);

  set_verbose(verbose);
  if(gtkrc && g_file_test(gtkrc, G_FILE_TEST_EXISTS))
    gtk_rc_parse(gtkrc);
  gui_set_glade_file(glade);

  Py_INCREF(Py_None);
  return Py_None;
}

static PyMethodDef base_methods[] = {
  { "init", (PyCFunction)init, METH_VARARGS | METH_KEYWORDS, doc_init },
  { "uninit", (PyCFunction)uninit, METH_VARARGS | METH_KEYWORDS, doc_uninit },
  { "command", (PyCFunction)command, METH_VARARGS, doc_command },
  {NULL, NULL, 0, NULL}
};

#ifdef __cplusplus
extern "C" {
#endif
DL_EXPORT(void)
initcpokerinterface(void)
{
  Py_InitModule("cpokerinterface", base_methods);
}
#ifdef __cplusplus
}
#endif

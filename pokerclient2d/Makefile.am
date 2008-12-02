#
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
#  Loic Dachary <loic@gnu.org>
#  Henry Prêcheur <henry@precheur.org> (2004)
#
INCLUDES = -Wstrict-prototypes

MAINTAINERCLEANFILES = \
	Makefile.in

SUBDIRS = data

pkglibdir=@pkglibdir@
pkgdatadir=@pkgdatadir@

EXTRA_DIST = \
	poker2d-test.xml \
	mingw_make_install.bat \
	Makefile.cygwin \
	Makefile.cygwin-sh \
	cygwin/setup.hint \
	$(wildcard cygwin/*.sh) \
	upgrades/1.0.7-1.0.8.xsl.in \
	poker2d.6.in \
	poker2d.in \
	poker2d.xml.in \
	run-interface \
	run-interface.bat \
	run-pokerserver \
	run-xwnc \
	poker2D_128.png \
	poker2D.ico \
	poker3d-interface/poker3d-interface.vcproj \
	khotkeys.py

man_MANS = poker2d.6

gamesdir = ${prefix}/games
games_SCRIPTS = poker2d

pkglib_PROGRAMS = poker-interface
poker_interface_SOURCES =	\
	network.c \
	main.c 
poker_interface_DEPENDENCIES = \
	libinterface.la
poker_interface_LDFLAGS = @GLADE_LIBS@ libinterface.la
poker_interface_CPPFLAGS = @GLADE_CFLAGS@ 

noinst_HEADERS = \
	gui.h \
	dispatcher.h \
	interface_io.h \
	util.h

noinst_LTLIBRARIES = \
	libinterface.la

libinterface_la_SOURCES = \
	util.c \
	gui.c \
	dispatcher.c \
	outfits.c \
	menu.c \
	chooser.c \
	sit_actions.c \
	yesno_message.c \
	tournaments.c \
	message_box.c \
	credits.c \
	login.c \
	blind.c \
	hand_history.c \
	chat.c \
	buy_in.c \
	lobby.c \
	cashier.c \
	muck.c \
	check_warning.c

libinterface_la_LDFLAGS = @GLADE_LIBS@
libinterface_la_CPPFLAGS = @GLADE_CFLAGS@ 

pyexec_LTLIBRARIES = _pokerinterface.la
_pokerinterface_la_SOURCES = python.c
_pokerinterface_la_DEPENDENCIES = libinterface.la
_pokerinterface_la_LDFLAGS = -module -no-undefined @GLIB_LIBS@ @GLADE_LIBS@ libinterface.la
_pokerinterface_la_CPPFLAGS = @GLADE_CFLAGS@ @PYTHON_CFLAGS@ @GLIB_CFLAGS@ -DPYTHON_VERSION=\"\" -D'VERSION_NAME(w)=w'

if PYTHON_2_6
py2_6exec_LTLIBRARIES = _pokerinterface2_6.la
_pokerinterface2_6_la_SOURCES = python.c
_pokerinterface2_6_la_DEPENDENCIES = libinterface.la
_pokerinterface2_6_la_LDFLAGS = -module -no-undefined @GLIB_LIBS@ @GLADE_LIBS@ libinterface.la
_pokerinterface2_6_la_CPPFLAGS = @GLADE_CFLAGS@ @PYTHON2_6_CFLAGS@ @GLIB_CFLAGS@ -DPYTHON_VERSION=\"2_6\" -D'VERSION_NAME(w)=w\#\#2_6'
endif

if PYTHON_2_5
py2_5exec_LTLIBRARIES = _pokerinterface2_5.la
_pokerinterface2_5_la_SOURCES = python.c
_pokerinterface2_5_la_DEPENDENCIES = libinterface.la
_pokerinterface2_5_la_LDFLAGS = -module -no-undefined @GLIB_LIBS@ @GLADE_LIBS@ libinterface.la
_pokerinterface2_5_la_CPPFLAGS = @GLADE_CFLAGS@ @PYTHON2_5_CFLAGS@ @GLIB_CFLAGS@ -DPYTHON_VERSION=\"2_5\" -D'VERSION_NAME(w)=w\#\#2_5'
endif

if PYTHON_2_4
py2_4exec_LTLIBRARIES = _pokerinterface2_4.la
_pokerinterface2_4_la_SOURCES = python.c
_pokerinterface2_4_la_DEPENDENCIES = libinterface.la
_pokerinterface2_4_la_LDFLAGS = -module -no-undefined @GLIB_LIBS@ @GLADE_LIBS@ libinterface.la
_pokerinterface2_4_la_CPPFLAGS = @GLADE_CFLAGS@ @PYTHON2_4_CFLAGS@ @GLIB_CFLAGS@ -DPYTHON_VERSION=\"2_4\" -D'VERSION_NAME(w)=w\#\#2_4'
endif

if PYTHON_2_3
py2_3exec_LTLIBRARIES = _pokerinterface2_3.la
_pokerinterface2_3_la_SOURCES = python.c
_pokerinterface2_3_la_DEPENDENCIES = libinterface.la
_pokerinterface2_3_la_LDFLAGS = -module -no-undefined @GLIB_LIBS@ @GLADE_LIBS@ libinterface.la
_pokerinterface2_3_la_CPPFLAGS = @GLADE_CFLAGS@ @PYTHON2_3_CFLAGS@ @GLIB_CFLAGS@ -DPYTHON_VERSION=\"2_3\" -D'VERSION_NAME(w)=w\#\#2_3'
endif

pokerclient2ddir = ${pythondir}/pokerclient2d
pokerclient2d_PYTHON = \
	__init__.py \
	poker2d.py \
	pokeranimation2d.py \
	pokerdisplay2d.py \
	pokerinterface2d.py \
	gamewindow.py

poker2ddir = ${pkgdatadir}/poker2d
nobase_dist_poker2d_DATA = \
	poker2d.xml \
	client.xml \
	upgrades/1.0.5-1.0.6.xsl \
	upgrades/1.0.6-1.0.7.xsl \
	upgrades/1.0.10-1.0.11.xsl \
	upgrades/1.0.23-1.0.24.xsl \
	upgrades/1.0.31-1.0.32.xsl \
	upgrades/str.replace.function.xsl

nobase_poker2d_DATA = \
	upgrades/1.0.7-1.0.8.xsl

pixmapsdir = ${datadir}/pixmaps
dist_pixmaps_DATA = \
	poker2D.xpm \
	poker2D-16.xpm 

applicationsdir = ${datadir}/applications
dist_applications_DATA = \
	python-poker2d.desktop

khotkeysdir = ${datadir}/apps/khotkeys
dist_khotkeys_DATA = poker2d.khotkeys

poker2d.khotkeys: khotkeys.py poker2d.xml
	srcdir=${srcdir} @PYTHON@ ${srcdir}/khotkeys.py > poker2d.khotkeys

#
# The python interpreter needs to find the binary modules immediately
# under the underware directory (underware.c_mafpacket for instance)
# and is using a search mechanism (based on PYTHONPATH) that can't
# cope with a directory hierarchy including a .libs
#
all-local:
	export PYTHONPATH=${top_srcdir}:${PYTHONPATH} ; \
	${POKERCONFIGUPGRADE} --verbose=1  --module=pokernetwork.pokernetworkconfig --upgrades=${srcdir}/upgrades ${srcdir}/poker2d.xml.in

install-data-hook:
	cp poker2d.xml $(DESTDIR)$(poker2ddir)/poker2d.xml.ref

uninstall-local:
	rm -f $(DESTDIR)$(poker2ddir)/poker2d.xml.ref

clean-local:
	rm -f *.pyc
	rm -f poker2d.khotkeys

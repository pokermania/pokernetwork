#
# Copyright (C) 2004, 2005, 2006 Mekensleep
#
# Mekensleep
# 24 rue vieille du temple
# 75004 Paris
#       licensing@mekensleep.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301, USA.
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
	Makefile.cygwin \
	Makefile.cygwin-sh \
	cygwin/setup.hint \
	$(wildcard cygwin/*.sh) \
	upgrades/1.0.7-1.0.8.xsl.in \
	upgrades/1.0.23-1.0.24.xsl \
	poker2d.6.in \
	poker2d.in \
	poker2d.xml.in \
	run-interface \
	run-interface.bat \
	run-pokerserver \
	run-xwnc \
	$(wildcard *.png) \
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
_pokerinterface_la_LDFLAGS = -module -no-undefined @GLIB_LIBS@ @PYTHON_LIBS@ @GLADE_LIBS@ libinterface.la
_pokerinterface_la_CPPFLAGS = @GLADE_CFLAGS@ @PYTHON_CFLAGS@ @GLIB_CFLAGS@ -DPYTHON_VERSION=\"\" -D'VERSION_NAME(w)=w'

if PYTHON_2_5
py2_5exec_LTLIBRARIES = _pokerinterface2_5.la
_pokerinterface2_5_la_SOURCES = python.c
_pokerinterface2_5_la_DEPENDENCIES = libinterface.la
_pokerinterface2_5_la_LDFLAGS = -module -no-undefined @GLIB_LIBS@ @PYTHON2_5_LIBS@ @GLADE_LIBS@ libinterface.la
_pokerinterface2_5_la_CPPFLAGS = @GLADE_CFLAGS@ @PYTHON2_5_CFLAGS@ @GLIB_CFLAGS@ -DPYTHON_VERSION=\"2_5\" -D'VERSION_NAME(w)=w\#\#2_5'
endif

if PYTHON_2_4
py2_4exec_LTLIBRARIES = _pokerinterface2_4.la
_pokerinterface2_4_la_SOURCES = python.c
_pokerinterface2_4_la_DEPENDENCIES = libinterface.la
_pokerinterface2_4_la_LDFLAGS = -module -no-undefined @GLIB_LIBS@ @PYTHON2_4_LIBS@ @GLADE_LIBS@ libinterface.la
_pokerinterface2_4_la_CPPFLAGS = @GLADE_CFLAGS@ @PYTHON2_4_CFLAGS@ @GLIB_CFLAGS@ -DPYTHON_VERSION=\"2_4\" -D'VERSION_NAME(w)=w\#\#2_4'
endif

if PYTHON_2_3
py2_3exec_LTLIBRARIES = _pokerinterface2_3.la
_pokerinterface2_3_la_SOURCES = python.c
_pokerinterface2_3_la_DEPENDENCIES = libinterface.la
_pokerinterface2_3_la_LDFLAGS = -module -no-undefined @GLIB_LIBS@ @PYTHON2_3_LIBS@ @GLADE_LIBS@ libinterface.la
_pokerinterface2_3_la_CPPFLAGS = @GLADE_CFLAGS@ @PYTHON2_3_CFLAGS@ @GLIB_CFLAGS@ -DPYTHON_VERSION=\"2_3\" -D'VERSION_NAME(w)=w\#\#2_3'
endif

pokerclient2ddir = ${pythondir}/pokerclient2d
pokerclient2d_PYTHON = \
	__init__.py \
	poker2d.py \
	pokeranimation2d.py \
	pokerdisplay2d.py \
	pokerinterface2d.py

poker2ddir = ${pkgdatadir}/poker2d
nobase_dist_poker2d_DATA = \
	poker2d.xml \
	client.xml \
	upgrades/1.0.5-1.0.6.xsl \
	upgrades/1.0.6-1.0.7.xsl \
	upgrades/1.0.10-1.0.11.xsl \
	upgrades/str.replace.function.xsl

nobase_poker2d_DATA = \
	upgrades/1.0.7-1.0.8.xsl

khotkeysdir = ${datadir}/apps/khotkeys
dist_khotkeys_DATA = poker2d.khotkeys

poker2d.khotkeys: khotkeys.py poker2d.xml.in
	@PYTHON@ ${srcdir}/khotkeys.py > poker2d.khotkeys

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

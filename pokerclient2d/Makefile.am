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
#  Henry Prêcheur <henry@precheur.org>
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
	poker2d.6.in \
	poker2d.in \
	poker2d.xml.in \
	run-interface \
	run-interface.bat \
	run-pokerserver \
	run-xwnc \
	poker3d-interface/poker3d-interface.vcproj

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

pokerclient2ddir = ${pyexecdir}/pokerclient2d

pokerclient2d_LTLIBRARIES = \
	cpokerinterface.la
cpokerinterface_la_SOURCES = \
	python.c
cpokerinterface_la_DEPENDENCIES = \
	libinterface.la
cpokerinterface_la_LDFLAGS = \
	-module -no-undefined @GLIB_LIBS@ @PYTHON_LIBS@ @GLADE_LIBS@ \
	libinterface.la
cpokerinterface_la_CPPFLAGS = \
	@GLADE_CFLAGS@ @PYTHON_CFLAGS@ @GLIB_CFLAGS@

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

#
# The python interpreter needs to find the binary modules immediately
# under the underware directory (underware.c_mafpacket for instance)
# and is using a search mechanism (based on PYTHONPATH) that can't
# cope with a directory hierarchy including a .libs
#
all-local:
	if [ -f .libs/*.so ] ; then \
		rm -f *.so ; ln -s .libs/*.so . ; \
	else \
		rm -f *.dll ; ln -s .libs/*.dll cpokerinterface.dll ; \
	fi
	export PYTHONPATH=${top_srcdir} ; \
	${POKERCONFIGUPGRADE} --verbose=1  --module=pokernetwork.pokernetworkconfig --upgrades=${srcdir}/upgrades ${srcdir}/poker2d.xml.in

install-data-hook:
	if [ "${MAYBE_PYTHON_VERSION}" ] ; then \
		cp -a $(DESTDIR)$(gamesdir)/poker2d $(DESTDIR)$(gamesdir)/poker2d${PYTHON_VERSION} ; \
	fi
	cp poker2d.xml $(DESTDIR)$(poker2ddir)/poker2d.xml.ref

install-exec-local:
	mkdir -p ${DESTDIR}/${pyexecdir}
	mkdir -p ${DESTDIR}/${pokerclient2ddir}
	if [ -f cpokerinterface.dll ] ; then \
		cp cpokerinterface.dll ${DESTDIR}/${pokerclient2ddir} ; \
	fi
	if [ -f cpokerinterface.so ] ; then \
		cp cpokerinterface.so ${DESTDIR}/${pokerclient2ddir} ; \
	fi

uninstall-local:
	rm -f $(DESTDIR)$(poker2ddir)/poker2d.xml.ref
	rm -f $(DESTDIR)$(gamesdir)/poker2d${PYTHON_VERSION}

clean-local:
	rm -f *.so *.dll *.pyc

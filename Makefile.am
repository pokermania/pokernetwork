#
# Copyright (C) 2004, 2005 Mekensleep
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
#
# 
ACLOCAL_AMFLAGS = -I config

if POKER2D
  POKER2D_SUBDIRS = pokerclient2d
else
  POKER2D_SUBDIRS = 
endif

SUBDIRS = ${POKER2D_SUBDIRS}

MAINTAINERCLEANFILES = \
	INSTALL \
	ABOUT-NLS \
	Makefile.in \
	aclocal.m4 \
	config.guess \
	config.rpath \
	config.h.in \
	config.sub \
	configure \
	depcomp \
	install-sh \
	ltmain.sh \
	missing \
	mkinstalldirs \
	compile \
	py-compile

pkgsysconfdir = ${sysconfdir}/${PACKAGE}
dist_pkgsysconf_DATA = \
	conf/poker.client.xml \
	conf/poker.bot.xml \
	conf/poker.server.xml

pokernetworkdir = ${pyexecdir}/pokernetwork
pokernetwork_PYTHON = \
	pokernetwork/client.py \
	pokernetwork/protocol.py \
	pokernetwork/server.py \
	pokernetwork/pokerserver.py \
	pokernetwork/pokerclient.py \
	pokernetwork/pokerchildren.py \
	pokernetwork/config.py \
	pokernetwork/__init__.py \
	pokernetwork/packets.py \
	pokernetwork/pokerpackets.py \
	pokernetwork/pokerbot.py \
	pokernetwork/user.py

pokeruidir = ${pyexecdir}/pokerui
pokerui_PYTHON = \
	pokerui/pokerrenderer.py \
	pokerui/pokerinterface.py \
	pokerui/pokerinteractor.py \
	pokerui/pokerdisplay.py \
	pokerui/__init__.py \
	pokerui/pokeranimation.py \
	pokerui/pokerchat.py

pokerdbdir=${pkgdatadir}
dist_pokerdb_DATA = \
	database/schema.sql

EXTRA_DIST = \
	bootstrap \
	config/python.m4 \
	examples/poker.bot.xml \
	examples/poker.server.xml \
	examples/poker.server-monotone.xml \
	examples/interface_dummy_server.py \
	examples/interface.py \
	examples/run-example

clean-local:
	rm -f */*.py[co]
	rm -f examples/*.log

install-data-hook:
	chmod 600 ${DESTDIR}${pkgsysconfdir}/poker.server.xml

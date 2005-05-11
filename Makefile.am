#
# Copyright (C) 2004 Mekensleep
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
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# Authors:
#  Loic Dachary <loic@gnu.org>
#
# 
ACLOCAL_AMFLAGS = -I config

MAINTAINERCLEANFILES = \
	py-compile \
	aclocal.m4 \
	config.guess \
	config.sub \
	configure \
	install-sh \
	missing \
	Makefile.in \
	INSTALL

pkgsysconfdir = ${sysconfdir}/${PACKAGE}
dist_pkgsysconf_DATA = \
	conf/poker.client.xml \
	conf/poker.bot.xml \
	conf/poker.server.xml

pythondir = ${pyexecdir}/pokernetwork
python_PYTHON = \
	pokernetwork/client.py \
	pokernetwork/protocol.py \
	pokernetwork/server.py \
	pokernetwork/pokerserver.py \
	pokernetwork/pokerclient.py \
	pokernetwork/config.py \
	pokernetwork/__init__.py \
	pokernetwork/packets.py \
	pokernetwork/pokerpackets.py \
	pokernetwork/pokerbot.py \
	pokernetwork/user.py

pokerdbdir=${pkgdatadir}

dist_pokerdb_DATA = \
	database/schema.sql

EXTRA_DIST = \
	bootstrap \
	config/python.m4 \
	examples/poker.bot.xml \
	examples/poker.server.xml \
	examples/poker.server-monotone.xml \
  examples/run-example

clean-local:
	rm -f */*.py[co]

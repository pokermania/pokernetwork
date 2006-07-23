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
#
# 
ACLOCAL_AMFLAGS = -I config

if POKER2D
  POKER2D_SUBDIRS = pokerclient2d
else
  POKER2D_SUBDIRS = 
endif

SUBDIRS = ${POKER2D_SUBDIRS} tests

pkglibdir=@pkglibdir@
pkgdatadir=@pkgdatadir@
pkgsysconfdir=@pkgsysconfdir@

MAINTAINERCLEANFILES = INSTALL Makefile.in aclocal.m4 configure \
	$(filter-out %.m4,$(wildcard config/[a-z]*)) 

nobase_dist_pkgdata_DATA = \
	conf/poker.client.xml \
	conf/poker.bot.xml \
	conf/poker.server.xml \
	conf/poker.pem \
	upgrades/poker.bot/1.0.5-1.0.6.xsl \
	upgrades/poker.bot/1.0.11-1.0.12.xsl \
	upgrades/poker.bot/1.0.14-1.0.15.xsl \
	upgrades/poker.client/1.0.5-1.0.6.xsl \
	upgrades/poker.client/1.0.11-1.0.12.xsl \
	upgrades/poker.client/1.0.12-1.0.13.xsl \
	upgrades/poker.client/1.0.14-1.0.15.xsl \
	upgrades/poker.server/1.0.5-1.0.6.xsl \
	upgrades/poker.server/1.0.11-1.0.12.xsl \
	upgrades/poker.server/1.0.12-1.0.13.xsl \
	upgrades/poker.server/1.0.13-1.0.14.xsl \
	upgrades/poker.server/1.0.14-1.0.15.xsl

pokernetworkdir = ${pyexecdir}/pokernetwork
pokernetwork_PYTHON = \
	pokernetwork/__init__.py \
	pokernetwork/client.py \
	pokernetwork/currencyclient.py \
	pokernetwork/dispatch.py \
	pokernetwork/packets.py \
	pokernetwork/pokeravatar.py \
	pokernetwork/pokerbot.py \
	pokernetwork/pokercashier.py \
	pokernetwork/pokerchildren.py \
	pokernetwork/pokerclient.py \
	pokernetwork/pokerdatabase.py \
	pokernetwork/pokerlock.py \
	pokernetwork/pokernetworkconfig.py \
	pokernetwork/pokerpackets.py \
	pokernetwork/pokerserver.py \
	pokernetwork/pokerservice.py \
	pokernetwork/pokertable.py \
	pokernetwork/protocol.py \
	pokernetwork/proxy.py \
	pokernetwork/server.py \
	pokernetwork/upgrade.py \
	pokernetwork/user.py \
	pokernetwork/version.py

man_MANS = \
	pokernetwork/pokerserver.8 \
	pokernetwork/pokerbot.8 \
	database/pokerdatabaseupgrade.8

sbin_SCRIPTS = \
	pokernetwork/pokerserver \
	pokernetwork/pokerbot \
	database/pokerdatabaseupgrade

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
	database/schema.sql \
	database/1.0.5-1.0.6.sql \
	database/1.0.6-1.0.7.sql \
	database/1.0.7-1.0.8.sql \
	database/1.0.11-1.0.12.sql \
	database/1.0.16-1.0.17.sql \
	database/1.0.17-1.0.18.sql \
	database/1.0.20-1.0.21.sql

pokerupgradesdir=${pkgdatadir}/upgrades
dist_pokerupgrades_DATA = \
	upgrade

pkgconfigdir = ${libdir}/pkgconfig
pkgconfig_DATA = poker-network.pc

EXTRA_DIST = \
	HACKING \
	NIHPHOBIA \
	config/python.m4 \
	config/ccpython.m4 \
	config/python-depends.m4 \
	examples/poker.bot.xml \
	examples/poker.server.xml \
	examples/poker.server-monotone.xml \
	examples/poker.server-cygwin.xml \
	examples/interface_dummy_server.py \
	examples/interface.py \
	examples/xmlrpc-soap.py \
	examples/run-pokerserver \
	examples/test-pokerweb \
	tests/upgrade.in \
	tests/pokerweb \
	database/pokerdatabaseupgrade.in \
        poker-network.pc.in \
        pokernetwork/pokerserver.in \
        pokernetwork/pokerserver.8.in \
        pokernetwork/pokerbot.in \
        pokernetwork/pokerbot.8.in \
        database/schema.sql.in \
        database/pokerdatabaseupgrade.8.in \
        conf/poker.bot.xml.in \
        conf/poker.client.xml.in \
        conf/poker.server.xml.in \
	$(wildcard pokerweb/pages/*.php) \
	$(wildcard pokerweb/pages/*.txt) \
	pokerweb/conf/constants.php.in \
	pokerweb/conf/htaccess \
	pokerweb/conf/apache.conf

clean-local:
	rm -f */*.py[co]
	rm -f examples/*.log
	rm -f pokerweb/pages/constants.php pokerweb/pages/constants.php.ref pokerweb/pages/.htaccess

all-local:
	export PYTHONPATH=${srcdir} ; \
	for file in bot client server ; do \
		${POKERCONFIGUPGRADE} --verbose=1 --module=pokernetwork.pokernetworkconfig --upgrades=${srcdir}/upgrades/poker.$$file ${srcdir}/conf/poker.$$file.xml.in ; \
	done ; \
	${POKERCONFIGUPGRADE} --verbose=1 --module=pokernetwork.pokernetworkconfig --upgrades=${srcdir}/upgrades/poker.server ${srcdir}/examples/poker.server.xml ${srcdir}/examples/poker.server-monotone.xml ; \
	${POKERCONFIGUPGRADE} --verbose=1 --module=pokernetwork.pokernetworkconfig --upgrades=${srcdir}/upgrades/poker.bot ${srcdir}/examples/poker.bot.xml

install-data-local:
	mkdir -p "${DESTDIR}${pkgsysconfdir}"
	cp ${srcdir}/conf/poker.pem "${DESTDIR}${pkgsysconfdir}"
	for file in bot client server ; do \
		cp conf/poker.$$file.xml "${DESTDIR}${pkgsysconfdir}" ; \
		export PYTHONPATH=${srcdir} ; \
		${POKERCONFIGUPGRADE} --verbose=1 --module=pokernetwork.pokernetworkconfig --upgrades=${srcdir}/upgrades/poker.$$file "${DESTDIR}${pkgsysconfdir}/poker.$$file.xml" ; \
	done
	chmod 600 "${DESTDIR}${pkgsysconfdir}/poker.server.xml"
	chmod u+w "${DESTDIR}${pkgsysconfdir}"

uninstall-local:
	rm -fr "${DESTDIR}${pkgsysconfdir}"

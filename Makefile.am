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

SUBDIRS = ${POKER2D_SUBDIRS} tests

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

nobase_dist_pkgdata_DATA = \
	conf/poker.client.xml \
	conf/poker.bot.xml \
	conf/poker.server.xml \
	conf/poker.pem \
	upgrades/poker.bot/1.0.5-1.0.6.xsl \
	upgrades/poker.client/1.0.5-1.0.6.xsl \
	upgrades/poker.server/1.0.5-1.0.6.xsl

pokernetworkdir = ${pyexecdir}/pokernetwork
pokernetwork_PYTHON = \
	pokernetwork/client.py \
	pokernetwork/protocol.py \
	pokernetwork/server.py \
	pokernetwork/pokerdatabase.py \
	pokernetwork/pokerserver.py \
	pokernetwork/pokerclient.py \
	pokernetwork/pokerchildren.py \
	pokernetwork/pokernetworkconfig.py \
	pokernetwork/__init__.py \
	pokernetwork/packets.py \
	pokernetwork/pokerpackets.py \
	pokernetwork/pokerbot.py \
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
	database/1.0.7-1.0.8.sql

pokerupgradesdir=${pkgdatadir}/upgrades
dist_pokerupgrades_DATA = \
	upgrade

pkgconfigdir = ${libdir}/pkgconfig
pkgconfig_DATA = poker-network.pc

EXTRA_DIST = \
	HACKING \
	NIHPHOBIA \
	bootstrap \
	config/python.m4 \
	config/ccpython.m4 \
	config/python-depends.m4 \
	examples/poker.bot.xml \
	examples/poker.server.xml \
	examples/poker.server-monotone.xml \
	examples/interface_dummy_server.py \
	examples/interface.py \
	examples/xmlrpc-soap.py \
	examples/run-example

clean-local:
	rm -f */*.py[co]
	rm -f examples/*.log

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

install-data-hook:
	if [ "${MAYBE_PYTHON_VERSION}" ] ; then \
		cp ${DESTDIR}${pkgconfigdir}/poker-network.pc ${DESTDIR}${pkgconfigdir}/poker-network${PYTHON_VERSION}.pc ; \
		for file in pokerserver pokerbot pokerdatabaseupgrade ; do \
			cp -a ${DESTDIR}${sbindir}/$$file ${DESTDIR}${sbindir)/$${file}${PYTHON_VERSION} ; \
		done ; \
	fi

uninstall-local:
	rm -fr "${DESTDIR}${pkgsysconfdir}"
	rm -f ${DESTDIR}${pkgconfigdir}/poker-network${MAYBE_PYTHON_VERSION}.pc
	for file in pokerserver pokerbot pokerdatabaseupgrade ; do \
		rm -f ${DESTDIR}${sbindir}/$${file}${MAYBE_PYTHON_VERSION} ; \
	done

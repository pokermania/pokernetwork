#
# Copyright (C) 2005, 2006 Mekensleep
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
MAINTAINERCLEANFILES = Makefile.in

EXTRA_DIST = \
	createdatabase \
	schema.sql \
	poker.server.xml \
	upgrade-rsync \
	conf/poker.bot.xml.in \
	conf/poker.client.xml.in \
	conf/poker.server.xml.in \
	conf/poker2d.xml.in \
	conf/client.xml \
	coverage.py \
	test-poker-interface.py \
	poker-interface-sid.supp \
	test-pokerdatabase \
	test-upgrade.py \
	vncpasswd

TESTS_ENVIRONMENT = ./run
#
# Do NOT sort entries because the order matters 
#
TESTS = coverage-reset \
	upgrade \
	test-clientserver.py \
	test-currencyclient.py \
	test-pokernetworkconfig.py \
	test-pokerdatabase.py \
	test-pokerservice.py \
	test-pokerclient.py \
	test-pokerlock.py \
	test-pokercashier.py \
	test-xmlrpc.py \
	test-pokerinteractor.py \
	test-pokerrenderer.py \
	testcurrency.php \
	coverage-report \
	poker-interface

.PHONY: coverage-reset coverage-report poker-interface testicurrency

export top_srcdir

clean-local:
	rm -fr .coverage annotated _trial_temp phpunit

#
# Copyright (C) 2008 Loic Dachary <loic@dachary.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
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
MAINTAINERCLEANFILES = \
	Makefile.in

pkgsysconfdir=@pkgsysconfdir@

pkgsysconf_DATA = poker.stats.xml

EXTRA_DIST = \
	poker.stats.xml.in \
	pokerstats.1.in

man_MANS = pokerstats.1

bin_SCRIPTS = pokerstats

pokerstatsdir = ${pythondir}/pokerstats
pokerstats_PYTHON = \
	__init__.py \
	stats.py \
	statslogic.py

TESTS_ENVIRONMENT = ./run
#
# Do NOT sort entries because the order matters 
#
TESTS = coverage-reset \
	test-stats.py \
	coverage-report

.PHONY: coverage-reset coverage-report

export top_srcdir
export MYSQL_TEST_DBHOST
export MYSQL_TEST_DBROOT
export MYSQL_TEST_DBROOT_PASSWORD
export MYSQL

clean-local:
	rm -fr .coverage annotated _trial_temp

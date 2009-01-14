#
# Copyright (C) 2009 Loic Dachary <loic@dachary.org>
#
# This software's license gives you freedom; you can copy, convey,
# propagate, redistribute and/or modify this program under the terms of
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
MAINTAINERCLEANFILES = \
	Makefile.in

confdir=@pkgdatadir@/conf

conf_DATA = poker.prizes.xml

EXTRA_DIST = \
	poker.prizes.xml.in

pokerprizesdir = ${pythondir}/pokerprizes
pokerprizes_PYTHON = \
	__init__.py \
	prizes.py \
	tourneyselectinfo.py 

pokerprizesdbdir=${pkgdatadir}/prizes
dist_pokerprizesdb_DATA = \
	schema.sql

TESTS_ENVIRONMENT = ./run
#
# Do NOT sort entries because the order matters 
#
TESTS = coverage-reset \
	test-prizes.py \
	coverage-report

.PHONY: coverage-reset coverage-report

export top_srcdir
export MYSQL_TEST_DBHOST
export MYSQL_TEST_DBROOT
export MYSQL_TEST_DBROOT_PASSWORD
export MYSQL

clean-local:
	rm -fr .coverage annotated _trial_temp

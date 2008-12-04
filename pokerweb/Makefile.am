#
# Copyright (C) 2006, 2007, 2008 Loic Dachary <loic@dachary.org>
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
MAINTAINERCLEANFILES = Makefile.in

EXTRA_DIST = \
	pages/tests/README \
	pages/tests/test-cash.html \
	pages/tests/test-create_account.html \
	pages/tests/test-edit_account.html \
	pages/tests/test-index.html \
	pages/tests/test-currencies.html \
	pages/tests/test-login.html \
	pages/tests/TestSuite.html

poker_web_sysconfdir = ${sysconfdir}/poker-web
dist_poker_web_sysconf_DATA = \
	conf/htaccess \
	conf/apache.conf

poker_web_databasedir = ${datadir}/poker-web/database
dist_poker_web_database_DATA = \
	database/schema.sql

poker_webdir = ${datadir}/poker-web
dist_poker_web_DATA = \
	pages/birthday.php \
	pages/cash_in.php \
	pages/cash_out.php \
	pages/common.php \
	pages/constants.php.ref \
	pages/country.txt \
	pages/create_account.php \
	pages/currency_one.php \
	pages/currency.php \
	pages/default-image.jpg \
	pages/edit_account.php \
	pages/footer_default.php \
	pages/header_default.php \
	pages/image.php \
	pages/index.php \
	pages/lib_filters.php \
	pages/login.php \
	pages/logout.php \
	pages/nusoap.php \
	pages/poker.php \
	pages/webservice.php \
	pages/prototype.js \
	pages/tilt.html

all-local:
	cd pages ; ln -fs constants.php.ref constants.php
	cd pages ; ln -fs ../conf/htaccess .htaccess

clean-local:
	rm -f pages/constants.php
	rm -f pages/.htaccess

install-data-local:
	mkdir -p ${DESTDIR}${poker_webdir}
	ln -fs ${poker_web_sysconfdir}/constants.php ${DESTDIR}${poker_webdir}/constants.php
	ln -fs ${poker_web_sysconfdir}/htaccess ${DESTDIR}${poker_webdir}/.htaccess

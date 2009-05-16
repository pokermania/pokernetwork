#
# Copyright (C) 2007, 2008 Loic Dachary <loic@dachary.org>
# Copyright (C) 2005, 2006 Mekensleep <licensing@mekensleep.com>
#                          24 rue vieille du temple, 75004 Paris
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
# Authors:
#  Loic Dachary <loic@dachary.org>
#
MAINTAINERCLEANFILES = Makefile.in

EXTRA_DIST = \
	createdatabase \
	schema.sql \
	poker.server.xml \
	pokersql.xml \
	pokersqlfail.xml \
	poker.test18pokerclient.xml \
	upgrade-rsync \
	conf/poker.bot.xml.in \
	conf/poker.client.xml.in \
	conf/poker.server.xml.in \
	conf/poker2d.xml.in \
	conf/client.xml \
	poker-engine/poker.1-2-no-limit.xml \
	poker-engine/poker.holdem.xml \
	test-pokerauth/pokerauth.py \
	coverage.py \
	monitorplugin.py \
	testfilter.py \
	testtourney_select_info.py \
	testtourney_select_info_no_call.py \
	testerrorfilter.py \
	finishedfilter.py \
	test-poker-interface.py \
	testpackets.py \
	testmessages.py \
	testsettings.xml \
	test-leak.py.in \
	test-leak-no-trial.py.in \
	test-leak-reference.py.in \
	test-leak-exarkun.py.in \
	poker-interface-sid.supp \
	test-pokerdatabase \
	test-pokerdisplay2d \
	test-pygame \
	vncpasswd \
	testclock.py \
	__init__.py \
	test-fc.py \
	setupMysqlVariables

if UNITTEST
if POKER2D
  TEST_CPART = test-unittestmain
else
  TEST_CPART = 
endif
else
  TEST_CPART = 
endif

TESTS_ENVIRONMENT = ./run
#
# Do NOT sort entries because the order matters 
#
TESTS = coverage-reset \
	upgrade \
	test-clientserver.py \
	test-currencyclient.py \
	test-pokernetworkconfig.py \
	test-packets.py \
	test-attrpack.py \
	test-userstats.py \
	test-pokeravatar.py \
	test-pokerpackets.py \
	test-pokerclientpackets.py \
	test-pokerbotlogic.py \
	test-pokerdatabase.py \
	test-pokerservice.py \
	test-pokerservice-load.py \
	test-pokersql.py \
	test-pokerauth.py \
	test-user.py \
	test-pokertable.py \
	test-pokerchildren.py \
	test-pokerclient.py \
	test-pokerexplain.py \
	test-pokergameclient.py \
	test-pokerlock.py \
	test-pokercashier.py \
	test-webservice.py \
	test-pokerinteractor.py \
	test-quit.py \
	test-pokerrenderer.py \
	test-protocol.py \
	test-upgrade.py \
	test-pokerinterface.py \
	test-string.py \
	test-pokerdisplay2d.py \
	test-pygame.py \
	test-svg2gtk.py \
	test-gamewindow.py \
	test-poker2d.py \
	test-pokersite.py \
	test-pokermemcache.py \
	test-proxyfilter.py \
	test-proxy.py \
	test-pokerserver.py \
	testcurrency.php \
	testpoker.php \
	testbirthday.php \
	testwebservice.php \
	coverage-report \
	poker-interface \
        ${TEST_CPART}        


if UNITTEST
if POKER2D

noinst_PROGRAMS = test-unittestmain

test_unittestmain_SOURCES = test-unittestmain.cpp \
                            test-unittestgui.cpp \
                            test-unittestlobby.cpp \
                            test-unittesttournaments.cpp \
                            test-unittestoutfits.cpp \
                            test-unittesthandhistory.cpp \
                            io_mockup.c

test_unittestmain_CPPFLAGS = @UNITTESTCPP_CFLAGS@ @GLADE_CFLAGS@ @PYTHON_CFLAGS@
test_unittestmain_LDFLAGS = @UNITTESTCPP_LIBS@ @GLADE_LIBS@ @top_builddir@/pokerclient2d/libinterface.la

endif
endif

.PHONY: coverage-reset coverage-report poker-interface 

export top_srcdir
export MYSQL_TEST_DBHOST
export MYSQL_TEST_DBROOT
export MYSQL_TEST_DBROOT_PASSWORD
export MYSQL

clean-local:
	rm -fr .coverage annotated _trial_temp phpunit
	rm -f test-pokerdisplay2d/*.pyc
	rm -f test-pygame/*.pyc

#
# Copyright (C) 2006 Jerome Jeannin <griim.work@gmail.com>
#
# This software's license gives you freedom; you can copy, convey,
# propogate, redistribute and/or modify this program under the terms of
# the GNU Affero General Public License (AGPL) as published by the Free
# Software Foundation, either version 3 of the License, or (at your
# option) any later version of the AGPL.
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
# =========================================================================
# AM_UNITTEST : Check if Unittest++ available 

AC_DEFUN([AM_UNITTEST],
[ 

AC_ARG_ENABLE(unittest, [  --disable-unittest do not build coverage unittest], [
    unittest=false                       # for AM_CONDITION
], [

   PKG_CHECK_MODULES(UNITTESTCPP, unittest++ >= 0.1, [unittest_enabled="yes"], [unittest_enabled="no"] )
   if test "$unittest_enabled" = "yes" ; then
     CPPFLAGS="$CPPFLAGS $UNITTESTCPP_CFLAGS"
     LIBS="$LIBS $UNITTESTCPP_LIBS"
     AC_DEFINE(USE_UNITTESTCPP, 1, [activate unittest++])
       
     unittest=true                        # for AM_CONDITION
   fi
])
AM_CONDITIONAL([UNITTEST], [test x$unittest = xtrue])     # For use in Makefile.am

])


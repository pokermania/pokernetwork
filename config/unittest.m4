#
# Copyright (C) 2006 Jerome Jeannin <griim.work@gmail.com>
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
AM_CONDITIONAL([COVERAGE], [test x$unittest = xtrue])     # For use in Makefile.am

])


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

# Process this file with autoconf to produce a configure script.

AC_PREREQ(2.54)
AC_INIT(poker-network, 1.0.4)
AC_CANONICAL_TARGET
AM_INIT_AUTOMAKE()
AM_CONFIG_HEADER([config.h])
AC_CONFIG_SRCDIR([pokernetwork/protocol.py])

# Checks for programs.
AC_PROG_MAKE_SET
AC_GNU_SOURCE
AC_PROG_CPP
AC_PROG_LIBTOOL

AM_MAINTAINER_MODE

AM_PATH_PYTHON([2.3])

#
# G++ specific debug and optimization flags
#
AC_ARG_ENABLE(debug,
    [  --enable-debug          build in debug mode (the default is to build in optimized mode)],
    [enable_debug=yes])
    
AC_ARG_ENABLE(poker2d, [  --disable-poker2d do not build a GTK based client], [
    poker2d=false			# for AM_CONDITION
], [
    if test "$GXX" = "yes" -a "$ac_test_CXXFLAGS" != set ; then
      if test "$enable_debug" = "yes" ; then
        CFLAGS="-pipe -g -Wall -W"
        CXXFLAGS="-pipe -g -Wall -Wpointer-arith"
      else
        CFLAGS="-pipe -O3 -Wall -W"
        CXXFLAGS="-pipe -O3 -Wall -Wpointer-arith"
      fi
    fi

    AC_EXEEXT
    AC_OBJEXT
    AC_ISC_POSIX
    AC_HEADER_STDC
    AC_C_INLINE
    
    AC_LANG(C)
    
    AM_CC_PYTHON(2.3, yes)
    
    PKG_CHECK_MODULES(GLIB, glib-2.0 >= 2.0, [], [AC_MSG_ERROR(glib2 is a mandatory library)])
    PKG_CHECK_MODULES(GLADE, libglade-2.0 >= 2.4.0, [], [AC_MSG_ERROR(glade2 is a mandatory library)])

    poker2d=true			# for AM_CONDITION
])

AM_CONDITIONAL([POKER2D], [test x$poker2d = xtrue])	# For use in Makefile.am

# Generate files
if test x$poker2d = xtrue
then
        AC_CONFIG_FILES([
        pokerclient2d/Makefile
        pokerclient2d/poker2d.6
        pokerclient2d/poker2d
        pokerclient2d/data/Makefile
        ])
fi
AC_CONFIG_FILES([Makefile])
AC_OUTPUT

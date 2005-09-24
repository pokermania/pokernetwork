#
# Copyright (C) 2002, 2005 Loic Dachary <loic@gnu.org>
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
# AM_CC_PYTHON : Python checking macros

AC_DEFUN([AM_CC_PYTHON],
[ 
AM_PATH_PYTHON($1)
AC_REQUIRE_CPP()

AC_CACHE_CHECK([for $am_display_PYTHON include directory],
    [am_cv_python_includedir],
    [am_cv_python_includedir=`$PYTHON -c "from distutils import sysconfig; print sysconfig.get_config_var('INCLUDEPY')" 2>/dev/null ||
     echo "$PYTHON_PREFIX/include/python$PYTHON_VERSION"`])
  AC_SUBST([pythonincludedir], [$am_cv_python_includedir])

AC_CACHE_CHECK([for $am_display_PYTHON C libraries directory],
    [am_cv_python_clibdir],
    [am_cv_python_clibdir=`$PYTHON -c "from distutils import sysconfig; print sysconfig.get_config_var('LIBPL')" 2>/dev/null ||
     echo "$PYTHON_PREFIX/lib/python$PYTHON_VERSION/config"`])
  AC_SUBST([pythonclibdir], [$am_cv_python_clibdir])

AC_CACHE_CHECK([for $am_display_PYTHON link flags],
    [am_cv_python_linkflags],
    [am_cv_python_linkflags=`$PYTHON -c "from distutils import sysconfig; print sysconfig.get_config_var('BLDLIBRARY')" 2>/dev/null ||
     echo "$PYTHON_PREFIX/lib/python$PYTHON_VERSION/config"`])
  AC_SUBST([pythonlinkflags], [$am_cv_python_linkflags])

PYTHON_CFLAGS="-I$pythonincludedir"
PYTHON_LIBS="-L$pythonclibdir $pythonlinkflags"

_CPPFLAGS="$CPPFLAGS"
CPPFLAGS="$CFLAGS ${PYTHON_CFLAGS}"

AC_MSG_NOTICE([Searching python includes in $pythonincludedir])

AC_CHECK_HEADER([Python.h],
      have_python_headers="yes",
      have_python_headers="no" )

dnl Test the libraries
AC_MSG_CHECKING(for Python libraries)

CPPFLAGS="$CFLAGS $PYTHON_CFLAGS"

AC_TRY_LINK( , , have_python_libraries="yes", have_python_libraries="no")

CPPFLAGS="$_CPPFLAGS"

if test "$have_python_libraries" = "yes"
then
    if test "$python_libraries"
    then
        AC_MSG_RESULT([$python_libraries])
    else
        AC_MSG_RESULT(yes)
    fi
else
    AC_MSG_RESULT(no)
fi

if test "$have_python_headers" = "yes" \
   && test "$have_python_libraries" = "yes"
then
    have_python="yes"
else
    have_python="no"
fi

if test "$have_python" = "no"
then
    AC_MSG_ERROR([Python is required to produce C++ based interpreter.])
fi

AC_SUBST(PYTHON_CFLAGS)
AC_SUBST(PYTHON_LIBS)

])

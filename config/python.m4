#
# Copyright (C) 2002 Loic Dachary <loic@gnu.org>
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

AC_DEFUN(AM_CC_PYTHON,
[ python_version_required="$1"

is_mandatory="$2"

AC_REQUIRE_CPP()

dnl Get from the user option the path to the Python files location
AC_ARG_WITH( python,
    [  --with-python=<path>    path to the Python prefix installation directory.
                          e.g. /usr/local],
    [ PYTHON_PREFIX=$with_python ]
)

AC_ARG_WITH( python-version,
    [  --with-python-version=<version>
                          Python version to use, e.g. 2.2],
    [ PYTHON_VERSION=$with_python_version ]
)

if test ! "$PYTHON_PREFIX" = ""
then
    PATH="$PYTHON_PREFIX/bin:$PATH"
fi

if test ! "$PYTHON_VERSION" = ""
then
    PYTHON_EXEC="python$PYTHON_VERSION"
else
    PYTHON_EXEC="python python2.2 python2.3"
fi

AC_PATH_PROGS(PYTHON, $PYTHON_EXEC, no, $PATH)

if test "$PYTHON" != "no"
then
  dnl Use the values of $prefix and $exec_prefix for the corresponding
  dnl values of PYTHON_PREFIX and PYTHON_EXEC_PREFIX.  These are made
  dnl distinct variables so they can be overridden if need be.  However,
  dnl general consensus is that you shouldn't need this ability.

  AC_SUBST(PYTHON_PREFIX)
  PYTHON_PREFIX='${prefix}'

  AC_SUBST(PYTHON_EXEC_PREFIX)
  PYTHON_EXEC_PREFIX='${exec_prefix}'
    PYTHON_VERSION=`$PYTHON -c 'import sys; print "%s" % (sys.version[[:3]])'`

    INSTALLED_PYTHON_PREFIX=`$PYTHON -c 'import sys; print "%s" % (sys.prefix)'`
    INSTALLED_PYTHON_EXEC_PREFIX=`$PYTHON -c 'import sys; print "%s" % (sys.exec_prefix)'`
    is_python_version_enough=`expr $python_version_required \<= $PYTHON_VERSION`
fi


if test "$PYTHON" = "no" || test "$is_python_version_enough" != "1"
then

    if test "$is_mandatory" = "yes"
    then
        AC_MSG_ERROR([Python $python_version_required must be installed (http://www.python.org)])
    else
        have_python="no"
    fi

else

    python_includes="$INSTALLED_PYTHON_PREFIX/include/python$PYTHON_VERSION"
    python_libraries="$INSTALLED_PYTHON_PREFIX/lib/python$PYTHON_VERSION/config"
    python_lib="python$PYTHON_VERSION"

    PYTHON_CFLAGS="-I$python_includes"
    PYTHON_LIBS="-L$python_libraries -l$python_lib"

    _CPPFLAGS="$CPPFLAGS"
    CPPFLAGS="$CFLAGS ${PYTHON_CFLAGS}"

    dnl Test the headers
    AC_MSG_CHECKING(for Python headers)

    AC_EGREP_CPP( yo_python,
    [#include <Python.h>
   yo_python
    ],
      have_python_headers="yes",
      have_python_headers="no" )

    if test "$have_python_headers" = "yes"
    then
        AC_MSG_RESULT([$python_includes])
    else
        AC_MSG_RESULT(no)
    fi

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

    if test "$have_python" = "no" -a "$is_mandatory" = "yes"
    then
        AC_MSG_ERROR([Python is required to produce C++ based interpreter.])
    fi

    AC_SUBST(PYTHON_CFLAGS)
    AC_SUBST(PYTHON_LIBS)

  dnl At times (like when building shared libraries) you may want
  dnl to know which OS platform Python thinks this is.

  AC_SUBST(PYTHON_PLATFORM)
  PYTHON_PLATFORM=`$PYTHON -c "import sys; print sys.platform"`


  dnl Set up 4 directories:

  dnl pythondir -- where to install python scripts.  This is the
  dnl   site-packages directory, not the python standard library
  dnl   directory like in previous automake betas.  This behaviour
  dnl   is more consistent with lispdir.m4 for example.
  dnl
  dnl Also, if the package prefix isn't the same as python's prefix,
  dnl then the old $(pythondir) was pretty useless.

  AC_SUBST(pythondir)
  pythondir=$PYTHON_PREFIX"/lib/python"$PYTHON_VERSION/site-packages

  dnl pkgpythondir -- $PACKAGE directory under pythondir.  Was
  dnl   PYTHON_SITE_PACKAGE in previous betas, but this naming is
  dnl   more consistent with the rest of automake.
  dnl   Maybe this should be put in python.am?

  AC_SUBST(pkgpythondir)
  pkgpythondir=\${pythondir}/$PACKAGE

  dnl pyexecdir -- directory for installing python extension modules
  dnl   (shared libraries)  Was PYTHON_SITE_EXEC in previous betas.

  AC_SUBST(pyexecdir)
  pyexecdir=$PYTHON_EXEC_PREFIX"/lib/python"$PYTHON_VERSION/site-packages

  dnl pkgpyexecdir -- $(pyexecdir)/$(PACKAGE)
  dnl   Maybe this should be put in python.am?

  AC_SUBST(pkgpyexecdir)
  pkgpyexecdir=\${pyexecdir}/$PACKAGE

fi

])

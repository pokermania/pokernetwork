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
# MY_CC_PYTHON : Python checking macros

AC_DEFUN([_ONE_CC_PYTHON],
[ 
AM_PATH_PYTHON($1,[],[unset PYTHON])
have_python="no"
if test "$PYTHON" ; then
    
    eval eval py]$2[execdir=${pyexecdir}
    AC_SUBST(py]$2[execdir)
    eval eval pkgpy]$2[execdir=${pkgpyexecdir}
    AC_SUBST(pkgpy]$2[execdir)

    AC_REQUIRE_CPP()
    
    AC_CACHE_CHECK([for $am_display_PYTHON$2 include directory],
        [am_cv_python]$2[_includedir],
        [am_cv_python]$2[_includedir=`$PYTHON -c "from distutils import sysconfig; print sysconfig.get_config_var('INCLUDEPY')" 2>/dev/null ||
         echo "$PYTHON_PREFIX/include/python$PYTHON_VERSION"`])
      AC_SUBST([python]$2[includedir], [$am_cv_python]$2[_includedir])
      AC_SUBST([python]$2[includedir], [$am_cv_python]$2[_includedir])
    
    AC_CACHE_CHECK([for $am_display_PYTHON C libraries directory],
        [am_cv_python]$2[_clibdir],
        [am_cv_python]$2[_clibdir=`$PYTHON -c "from distutils import sysconfig; print sysconfig.get_config_var('LIBPL')" 2>/dev/null ||
         echo "$PYTHON_PREFIX/lib/python$PYTHON_VERSION/config"`])
      AC_SUBST([python]$2[clibdir], [$am_cv_python]$2[_clibdir])
    
    AC_CACHE_CHECK([for $am_display_PYTHON link flags],
        [am_cv_python]$2[_linkflags],
        [
    case $build_os in
      cygwin* | mingw*)
            am_cv_python]$2[_linkflags='-lpython2.4' ;;
      *)
            am_cv_python]$2[_linkflags=`$PYTHON -c "from distutils import sysconfig; print '-L' + sysconfig.get_config_var('LIBPL')" 2>/dev/null || echo "-L$PYTHON_PREFIX/lib/python$PYTHON_VERSION/config"`
            am_cv_python]$2[_linkflags="$am_cv_python]$2[_linkflags -lpython$PYTHON_VERSION"
            ;;
    esac
            
     ])
      AC_SUBST([python]$2[linkflags], [$am_cv_python]$2[_linkflags])
    
    PYTHON_CFLAGS="-I$python]$2[includedir"
    PYTHON_LIBS="-L$python]$2[clibdir $python]$2[linkflags"
    
    _CPPFLAGS="$CPPFLAGS"
    CPPFLAGS="$CPPFLAGS ${PYTHON_CFLAGS}"
    
    echo checking python includes in $python]$2[includedir
    
    unset ac_cv_header_Python_h
    AC_CHECK_HEADER([Python.h],
          have_python_headers="yes",
          have_python_headers="no" )
    
    dnl Test the libraries
    AC_MSG_CHECKING(for Python libraries)
    
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
      AC_MSG_WARN([No python compilation environment for $1])
    else
      [PYTHON]$2[_CFLAGS]="${PYTHON_CFLAGS}"
      AC_SUBST([PYTHON]$2[_CFLAGS])
      AC_SUBST(PYTHON_CFLAGS)
    
      [PYTHON]$2[_LIBS]="${PYTHON_LIBS}"
      AC_SUBST([PYTHON]$2[_LIBS])
      AC_SUBST(PYTHON_LIBS)
      AC_MSG_NOTICE([Found working python compilation environment for $1])
    fi
fi
AM_CONDITIONAL([PYTHON_]$2, [test "$have_python" != "no"])
])

AC_DEFUN([ALL_CC_PYTHON],
[ 
m4_define([_AM_PYTHON_INTERPRETER_LIST], [python2.5 python2.4 python2.3])
found_one=''
_ONE_CC_PYTHON([=2.3], [2_3])
if test -f "$PYTHON" ; then found_one=$PYTHON ; fi
unset PYTHON
_ONE_CC_PYTHON([=2.4], [2_4])
if test -f "$PYTHON" ; then found_one=$PYTHON ; fi
unset PYTHON
_ONE_CC_PYTHON([=2.5], [2_5])
#
# python2.5 support in dependencies is not mature yet
#
#if test -f "$PYTHON" ; then found_one=$PYTHON ; fi
PYTHON=$found_one
if ! test "$found_one" ; then
   AC_MSG_ERROR([No python development environments found])
fi
])

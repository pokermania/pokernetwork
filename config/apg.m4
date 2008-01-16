# Copyright (C) 2008 Bradley M. Kuhn <bkuhn@ebb.org>
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
#   Bradley M. Kuhn <bkuhn@ebb.org>

# **************************************************************************
#                POKERNETWORK_AC_PROG_APG - TEST FOR apg

# POKERNETWORK_AC_PROG_APG is a function to test to see if we have a version of
# apg needed.

# Usage:
# POKERNETWORK_AC_PROG_APG(
# POKERNETWORK_AC_PROG_APG([MINIMUM-VERSION, [ACTION-IF-USER-REFUSED, [ACTION-IF-FOUND [, ACTION-IF-NOT-FOUND]]]])
# 
# Example:
# POKERNETWORK_AC_PROG_APG(2.2, AC_MSG_ERROR([*** What have you got against apg? ***]), , AC_MSG_ERROR([*** apg >= 2.2 is not installed - please install first ***]))
#
# Defines apg, and apg_VERSION

AC_DEFUN([POKERNETWORK_AC_PROG_APG],
[#
# min_apg_version is the minimal version of apg.  It defaults to 2.2
# if none is given.

min_apg_version=ifelse([$1], ,2.2, $1)
ignore_apg=

AC_ARG_WITH(apg,            [  --with-apg=PROGRAM            Full path of the apg binary (defaults to yes)],
            if test "x$withval" == "xno" ; then
               ignore_apg=yes
            else
              apg_path="$withval"
            fi, apg_path="")

if test x$apg_path != x ; then
    if test x${APG+set} != xset ; then
        APG=$apg_path
    fi
fi

if test x$ignore_apg != x; then
   AC_MSG_WARN(not using apg)
   ifelse([$2], , :, [$2])
else
# Now, check the path for APG, unless APG is already set

  AC_PATH_PROG(APG, [apg], no)

  if test "$APG" = "no" ; then
      ifelse([$2], , :, [$2])
  else
      # check that we have the right version

      AC_MSG_CHECKING(for apg - version >= $min_apg_version)

      APG_VERSION=`$APG -v 2>&1 | grep '^version *[[0-9\.]]' | sed 's/^version *\([[0-9\.a-zA-Z]]*\) .*/\1/'`

      apg_version_have_major=`echo $APG_VERSION | sed 's/^\([[0-9]]*\)\.\([[0-9]]*\).*$/\1/'`
      apg_version_have_minor=`echo $APG_VERSION | sed 's/^\([[0-9]]*\)\.\([[0-9]]*\).*$/\2/'`
      min_apg_version_major=`echo $min_apg_version | sed 's/^\([[0-9]]*\)\.\([[0-9]]*\).*$/\1/'`
      min_apg_version_minor=`echo $min_apg_version | sed 's/^\([[0-9]]*\)\.\([[0-9]]*\).*$/\2/'`
     if test -z "$APG_VERSION";
     then
        AC_MSG_RESULT(no)
	AC_MSG_WARN([apg was found, but it its version could not be determined.])
        ifelse([$4], , :, [$4])
     elif test \( $min_apg_version_major -gt $apg_version_have_major \) -o \
          \( \( $min_apg_version_major -le $apg_version_have_major \) -a \
            \( $min_apg_version_minor -gt $apg_version_have_minor \) \) ; \
     then
        AC_MSG_RESULT(no)
	AC_MSG_WARN([apg was found, but it was only version $APG_VERSION.])
        ifelse([$4], , :, [$4])
     else
        AC_MSG_RESULT(yes)
        ifelse([$3], , :, [$3])
     fi
     AC_SUBST(APG)
     AC_SUBST(APG_VERSION)
  fi
fi
])

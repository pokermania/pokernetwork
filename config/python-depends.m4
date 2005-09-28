#
# Copyright (C) 2005 Loic Dachary <loic@gnu.org>
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
# AM_PYTHON_DEPENDS : check python dependencies

AC_DEFUN([AM_PYTHON_DEPENDS],
[ 

AC_ARG_ENABLE(python-depends,
[  --disable-python-depends
                          disable python dependencies check (enabled by default). ],[python_depends=/bin/false],
[
python_depends=/bin/true

python_script="
import imp
import sys

path = list()
modules = sys.argv.pop(1)
for module in modules.split('.'):
        (file,  pathname, info) = imp.find_module(module, sys.path + path)
        sys.stdout.write(pathname + ' ')
        path = list(( pathname, ))
"
for module in $1 ; do
    AC_MSG_CHECKING([wether python module $module is available])
    if $PYTHON -c "$python_script" $module ; then
       AC_MSG_RESULT([... yes])
    else
       AC_MSG_ERROR([failed])
    fi
done

])

])

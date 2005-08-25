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
AC_INIT(poker-network, [esyscmd(perl -n -e "print if(s/^version_number = \"(.*)\".*/\1/s)" pokernetwork/__init__.py)])
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

AC_PATH_PROG(RSYNC, [rsync])
AC_PATH_PROG(MYSQL, [mysql])

AM_PATH_PYTHON([2.3])

PKG_CHECK_MODULES(POKER_ENGINE, poker-engine >= 1.0.6, [AC_MSG_RESULT([ok])], [AC_MSG_ERROR(poker-engine is a mandatory library)])
AC_SUBST(POKERCONFIGUPGRADE, [`pkg-config --variable=pokerconfigupgrade poker-engine`])

#
# G++ specific debug and optimization flags
#
AC_ARG_ENABLE(debug,
    [  --enable-debug          build in debug mode (the default is to build in optimized mode)],
    [enable_debug=yes])
    
AC_ARG_ENABLE(upgrades,
    [  --enable-upgrades       upgrades are automatically installed from the specified server (default off)],
    [enable_upgrades=yes],
    [enable_upgrades=no])
AC_SUBST(UPGRADES_ENABLE, $enable_upgrades)
AC_SUBST(UPGRADES_SOURCE, $enableval)

test x$prefix = xNONE && prefix="$ac_default_prefix"

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
    
    PKG_CHECK_MODULES(GLIB, glib-2.0 >= 2.0, [AC_MSG_RESULT([ok])], [AC_MSG_ERROR(glib2 is a mandatory library)])
    PKG_CHECK_MODULES(GLADE, libglade-2.0 >= 2.4.0, [AC_MSG_RESULT([ok])], [AC_MSG_ERROR(glade2 is a mandatory library)])

    AC_SUBST(POKER2D_PKGDATADIR, [`eval echo $datadir/$PACKAGE/poker2d`])

    poker2d=true			# for AM_CONDITION
])

AM_CONDITIONAL([POKER2D], [test x$poker2d = xtrue])	# For use in Makefile.am

AC_SUBST(POKER_PREFIX, [$prefix])
AC_SUBST(POKER_PYTHONDIR, [`eval echo $pythondir`])
AC_SUBST(POKER_NETWORK_PKGDATADIR, [`eval echo $datadir/$PACKAGE`])
AC_SUBST(POKER_NETWORK_PKGSYSCONFDIR, [`eval echo $sysconfdir/$PACKAGE`])
AC_SUBST(POKER_ENGINE_PKGSYSCONFDIR, [`pkg-config --variable=pkgsysconfdir poker-engine`])

AC_ARG_WITH(poker-server-host,
[  --with-poker-server-host=<hostname>
                          fully qualified host name of the 
                          default poker server to which the
                          poker client will connect (default localhost). ],
    [ POKER_SERVER_HOST=$with_poker_server_host ],
    [ POKER_SERVER_HOST=localhost ] )
AC_SUBST(POKER_SERVER_HOST)

AC_ARG_WITH(poker-database,
[  --with-poker-database=<name>
                          name of the MySQL database the poker
                          server will use to store information. 
                          (default pokernetwork)],
    [ POKER_DATABASE=$with_poker_database ],
    [ POKER_DATABASE=pokernetwork ] )
AC_SUBST(POKER_DATABASE)

AC_ARG_WITH(poker-dbhost,
[  --with-poker-dbhost=<hostname>
                          hostname of the MySQL server (default localhost). ],
    [ POKER_DBHOST=$with_poker_dbhost ],
    [ POKER_DBHOST=localhost ] )
AC_SUBST(POKER_DBHOST)

AC_ARG_WITH(poker-dbuser,
[  --with-poker-dbuser=<user>
                          user name to connect to the database (default pokernetwork). ],
    [ POKER_DBUSER=$with_poker_dbuser ],
    [ POKER_DBUSER=pokernetwork ] )
AC_SUBST(POKER_DBUSER)

AC_ARG_WITH(poker-dbuser-password,
[  --with-poker-dbuser-password=<password>
                          password for the user used to 
                          connect to the database (default pokernetwork). ],
    [ POKER_DBUSER_PASSWORD=$with_poker_dbuser_password ],
    [ POKER_DBUSER_PASSWORD=pokernetwork ] )
AC_SUBST(POKER_DBUSER_PASSWORD)

# Generate files
if test x$poker2d = xtrue
then
        AC_CONFIG_FILES([
        pokerclient2d/Makefile
        pokerclient2d/poker2d.6
        pokerclient2d/poker2d
        pokerclient2d/poker2d.xml
        pokerclient2d/data/Makefile
        ])
fi
AC_CONFIG_FILES([
        tests/upgrade
        database/pokerdatabaseupgrade
], [chmod +x $ac_file])
AC_CONFIG_FILES([
        poker-network.pc
        pokernetwork/pokerserver
        pokernetwork/pokerserver.8
        pokernetwork/pokerbot
        pokernetwork/pokerbot.8
        database/schema.sql
        database/pokerdatabaseupgrade.8
        conf/poker.bot.xml
        conf/poker.client.xml
        conf/poker.server.xml
        tests/Makefile
        Makefile
])
AC_OUTPUT

cat <<!

If this is your first installation, you will have to manually create
the MySQL database $POKER_DATABASE, create the MySQL user
$POKER_DBUSER with password $POKER_DBUSER_PASSWORD, give it permissions
on the $POKER_DATABASE database and populate the $POKER_DATABASE database.

        mysqladmin -h $POKER_DBHOST -u root -p create $POKER_DATABASE
        mysql -h $POKER_DBHOST -u root -p $POKER_DATABASE < database/schema.sql 
        mysql -h $POKER_DBHOST -u root -p -e "insert into user (Host, User, Password, Select_priv, Insert_priv, Update_priv, Delete_priv) values ('YOUR_HOSTNAME', '$POKER_DBUSER', password('$POKER_DBUSER_PASSWORD'), 'Y', 'Y', 'Y', 'Y')" mysql
        mysqladmin -h $POKER_DBHOST -u root -p reload

If you already have a previous version installed, you must upgrade
your database using:

database/pokerdatabaseupgrade --upgrades=database conf/poker.server.xml

!

#
# Copyright (C) 2007 Loic Dachary <loic@dachary.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
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
ulimit -n 10240
server=$1
shift
for i in $@ ; do
    perl -pi -e "s|<servers>.*</servers>|<servers>$server</servers>|" poker.bot${i}00.xml
    nohup python -u /usr/sbin/pokerbot poker.bot${i}00.xml > bot-$i.out 2>&1 &
done
tail -f bot-?.out

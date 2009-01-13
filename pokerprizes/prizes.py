#
# -*- coding: iso-8859-1 -*-
#
# Copyright (C) 2009 Loic Dachary <loic@dachary.org>
#
# This software's license gives you freedom; you can copy, convey,
# propagate, redistribute and/or modify this program under the terms of
# the GNU Affero General Public License (AGPL) as published by the Free
# Software Foundation (FSF), either version 3 of the License, or (at your
# option) any later version of the AGPL published by the FSF.
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
import os

from pokernetwork.pokernetworkconfig import Config

class PokerPrizes:
    def __init__(self, service):
        self.settings = Config(service.settings.dirs).headerGetProperties('/settings')
        create = False
        for table in ( self.settings['tourneys_schedule2prizes'], self.settings['prizes'] ):
            self.db.db.query("SHOW TABLES LIKE '%s'" % table)
            result = self.db.db.store_result()
            if result.num_rows() <= 0:
                create = True
            del result
        if create:
            parameters = service.settings.headerGetProperties("/server/database")[0]            
            cmd = self.mysql_command + " --host='" + parameters["host"] + "' --user='" + parameters["root_user"] + "' --password='" + parameters["root_password"] + "' '" + parameters["name"] + "' < " + self.settings["schema"]
            if self.verbose:
                self.message(cmd)
            os.system(cmd)

    def message(self, string):
        print "PokerPrizes: " + string

    def error(self, string):
        self.message("*ERROR* " + string)
        

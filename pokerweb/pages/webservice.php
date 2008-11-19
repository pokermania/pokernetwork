<?php // -*- php -*-
// Copyright (C) 2007 Mekensleep <licensing@mekensleep.com>
//                    24 rue vieille du temple, 75004 Paris
//
// This software's license gives you freedom; you can copy, convey,
// propogate, redistribute and/or modify this program under the terms of
// the GNU Affero General Public License (AGPL) as published by the Free
// Software Foundation (FSF), either version 3 of the License, or (at your
// option) any later version of the AGPL published by the FSF.
//
// This program is distributed in the hope that it will be useful, but
// WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero
// General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program in a file in the toplevel directory called
// "AGPLv3".  If not, see <http://www.gnu.org/licenses/>.
//
// Authors:
//  Johan Euphrosine <proppy@aminche.com>
//


if (sizeof($_GET) != 0) {
   require_once 'common.php';
   print handle_packet($poker, $_GET);
}

function handle_packet($poker, $packet) {
	 $result = $poker->send($packet);
	 return json_encode($result);
}

?>
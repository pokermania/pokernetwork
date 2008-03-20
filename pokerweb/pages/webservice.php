<?php // -*- php -*-
// Copyright (C) 2007 Mekensleep
//
// Mekensleep
// 24 rue vieille du temple
// 75004 Paris
//       licensing@mekensleep.com
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program; if not, write to the Free Software
// Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301, USA.
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
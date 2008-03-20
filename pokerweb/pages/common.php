<?php
//
// Copyright (C) 2006, 2007, 2008 Loic Dachary <loic@dachary.org>
// Copyright (C) 2005, 2006 Mekensleep
//
// Mekensleep
// 24 rue vieille du temple
// 75004 Paris
//       licensing@mekensleep.com
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
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
//  Loic Dachary <loic@gnu.org>
//  Morgan Manach <akshell@free.fr>
//

require_once 'constants.php';
require_once 'lib_filters.php';
require_once 'poker.php';

$hci_header_showed = false;

function hci_header() {
  require_once _cst_header;
}

function hci_footer() {
  require_once _cst_footer;
}

function no_auth_handler($name, $referer) {
  header('Location: login.php?name=' . $name . '&referer=' . urlencode($referer));
  die();
}

try {
  $poker = new poker(_cst_poker_soap_host);
} catch(Exception $e) {
  print "<h3>" . $e->getMessage() . "</h3d>";
  die();
}

$poker->setNoAuthHandler('no_auth_handler');
$poker->setTimeoutCookie(_cst_timeout_cookie);
  

?>

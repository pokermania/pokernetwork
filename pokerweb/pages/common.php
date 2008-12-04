<?php
//
// Copyright (C) 2006, 2007, 2008 Loic Dachary <loic@dachary.org>
// Copyright (C) 2005, 2006 Mekensleep <licensing@mekensleep.com>
//                          24 rue vieille du temple, 75004 Paris
//
// This software's license gives you freedom; you can copy, convey,
// propagate, redistribute and/or modify this program under the terms of
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

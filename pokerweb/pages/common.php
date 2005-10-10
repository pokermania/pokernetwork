<?php
//
// Copyright (C) 2005 Mekensleep
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
//  Morgan Manach <akshell@free.fr>
//  Loic Dachary <loic@gnu.org>
//

require_once 'constants.php';
require_once 'lib_filters.php';
require_once 'class.poker.php';

$hci_header_showed = false;

function hci_header($default = '') {
  global $hci_header_showed;

  if ($hci_header_showed)
    return;
      ?>
      <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">
         <html>
         <head>
         <title>PokerNetwork</title>
         <meta http-equiv="Content-Type" content="text/html; charset=<?php echo _cst_encoding; ?>">	
         </head>
         <body>
         <h1><a href="./">PokerNetwork</a></h1>
         <?php
         $hci_header_showed = true;
}

function hci_footer() {
            
      ?>
      </body>
          </html>
          <?php
          }

function no_auth_handler($name, $referer) {
  header('Location: login.php?name=' . $name . '&referer=' . urlencode($referer));
  die();
}

$poker_error = null;

function error_handler($type, $code, $message) {
  global $poker_error;

  $poker_error = $message;
}

$poker = new poker(_cst_poker_soap_host);
$poker->setErrorHandler('error_handler');
$poker->setNoAuthHandler('no_auth_handler');
$poker->setTimeoutCookie(_cst_timeout_cookie);

?>

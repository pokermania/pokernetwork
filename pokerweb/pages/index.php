<?php
//
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
//  Morgan Manach <akshell@free.fr>
//  Loic Dachary <loic@gnu.org>
//
require_once 'common.php';

$is_logged_in = $poker->isLoggedin();

hci_header();

print "<h3>" . _get_string('comment') . "</h3>";

if($is_logged_in) {
  $info = $poker->getPersonalInfo();
  echo '<h2>'.$infos['name'].'</h2>';
  echo '<!-- HOME IS LOGGED IN -->';
  echo '<a href="logout.php">logout</a><br>';
  echo '<a href="edit_account.php">Edit Account</a><br>';
} else {
  echo '<!-- HOME NOT LOGGED IN -->';
  echo '<a href="login.php">login</a><br>';
  echo '<a href="create_account.php">Create Account</a><br>';
}

hci_footer();
?>

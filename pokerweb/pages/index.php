<?php
//
// Copyright (C) 2006, 2007, 2008 Loic Dachary <loic@dachary.org>
// Copyright (C) 2005, 2006 Mekensleep <licensing@mekensleep.com>
//                          24 rue vieille du temple, 75004 Paris
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
//  Loic Dachary <loic@dachary.org>
//  Morgan Manach <akshell@free.fr> (2006)
//
require_once 'common.php';

try {
  $user_info = $poker->isLoggedin();
} catch(Exception $e) {
  print "<h3>" . $e->getMessage() . "</h3>";
  die();
}

if($poker_error) print "<h3>" . $poker_error . "</h3>";

hci_header();

print "<h3>" . _get_string('comment') . "</h3>";

if($user_info) {
  if($poker_error) print "<h3>" . $poker_error . "</h3>";
  echo '<h2>'.$user_info['name'].'</h2>';
  echo '<!-- HOME IS LOGGED IN -->';
  if(is_array($user_info['money'])) {
    foreach ( $user_info['money'] as $currency => $state ) {
      print _('bankroll')." ".substr($state[0], 0, -2).".".substr($state[0], -2).", "._('in game')." ".$state[1].", "._('point')." ".$state[2]." ("._('currency')." ".$currency.")<p>";
    }
  }
  echo '<a href="logout.php" id="logout">'._('Log out').'</a><br>';
  echo '<a href="edit_account.php" id="edit_account">'._('Edit Account').'</a><br>';
  echo '<a href="cash_in.php" id="cash_in">'._('Cash-In').'</a><br>';
  echo '<a href="cash_out.php" id="cash_out">'._('Cash-Out').'</a><br>';
} else {
  echo '<!-- HOME NOT LOGGED IN -->';
  echo '<a href="login.php" id="login">'._("Log in").'</a><br>';
  echo '<a href="create_account.php" id="create_account">'._('Create Account').'</a><br>';
}

hci_footer();
?>

<?php
//
// Copyright (C) 2006, 2007 Loic Dachary <loic@dachary.org>
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

$name = _get_string('name', _post_string('login'));
$referer = _post_string('referer', _get_string('referer', './'));

if(_post_string('submit')) {
  $login = _post_string('login');
  $password = _post_string('password');

  try {
    $poker->login($login, $password);
    header('Location: ' . $referer);
    die();
  } catch(Exception $e) {
    $poker_error = $e->getMessage();
  }
}

hci_header();

if($poker_error) {
  print "<!-- LOGIN ERROR PAGE " . $name . " -->";
  print "<h3>" . $poker_error . "</h3>";
}

?>
<!-- LOGIN FORM <?php echo $name ?> -->
<div>
	<form method="post">
		<div>
			<input type="hidden" name="referer" value="<?php echo $referer; ?>" />
		</div>
		<table>
			<tr>
				<td></td>
				<td>Login</td>
			</tr>
			<tr>
				<td><b>Login:</b></td>
				<td><input type="text" maxlength="32" name="login" value="<?php echo $name?>" /></td>
			</tr>
			<tr>
				<td><b>Password:</b></td>
				<td><input type="password" maxlength="32" name="password" id="password" /></td>
			</tr>
			<tr>
				<td></td>
				<td><a href="create_account.php">Create account</a></td>
			</tr>
			<tr>
				<td></td>
				<td><input type="submit" name='submit' value="Ok" /></td>
			</tr>
		</table>
	</form>
</div>
<?php
	hci_footer();
?>

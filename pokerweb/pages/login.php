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
//  Morgan Manach <akshell@free.fr> (2006)
//  Loic Dachary <loic@dachary.org>
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
				<td><? echo _('Login') ?></td>
			</tr>
			<tr>
				<td><b><? echo _('Login') ?>:</b></td>
				<td><input type="text" maxlength="32" name="login" value="<?php echo $name?>" /></td>
			</tr>
			<tr>
				<td><b><? echo _('Password') ?>:</b></td>
				<td><input type="password" maxlength="32" name="password" id="password" /></td>
			</tr>
			<tr>
				<td></td>
				<td><a href="create_account.php"><? echo _('Create Account') ?></a></td>
			</tr>
			<tr>
				<td></td>
				<td><input type="submit" name='submit' value="<? echo _('Ok') ?>" /></td>
			</tr>
		</table>
	</form>
</div>
<?php
	hci_footer();
?>

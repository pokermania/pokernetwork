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

function validate() {
  global $poker;
  global $poker_error;

  $login = _post_string('login');
  $password = _post_string('password');
  $password2 = _post_string('password2');
  $email = _post_string('email');
  $firstname = _post_string('firstname');
  $lastname = _post_string('lastname');
  $addr_street = _post_string('addr_street');
  $addr_street2 = _post_string('addr_street2');
  $addr_zip = _post_string('addr_zip');
  $addr_town = _post_string('addr_town');
  $addr_state = _post_string('addr_state');
  $addr_country = _post_string('addr_country');
  $phone = _post_string('phone');

  if ($password != $password2) {
    $poker_error = 'Password and confirmation must be the same.';
    return false;
  }
  $packets = $poker->send(array('type' => 'PacketPokerCreateAccount', 
                                'name' => $login, 
                                'password' => $password,
                                'email' => $email,
                                'firstname' => $firstname,
                                'lastname' => $lastname,
                                'addr_street' => $addr_street,
                                'addr_street2' => $addr_street2,
                                'addr_zip' => $addr_zip,
                                'addr_town' => $addr_town,
                                'addr_state' => $addr_state,
                                'addr_state' => $addr_country,
                                'phone' => $phone
                                ));

  if($packets == null || $packets[0]['type'] != 'PacketPokerPersonalInfo') {
    return false;
  }

  return $poker->login($login, $password);
}

if(_post_string('submit') && validate()) {
  header('Location: index.php?comment=Account%20created.');
  die();
}

	$login = _get_string('name');

	hci_header();

if($poker_error) {
  print "<!-- CREATE ACCOUNT ERROR PAGE " . $login . " -->";
  print "<h3>" . $poker_error . "</h3>";
}

?>
<!-- CREATE ACCOUNT <?php echo $login ?> -->

	<form method="post">
		<table>
			<tr>
				<td></td>
				<td>Create Account</td>
			</tr>
			<tr>
				<td><b>Login:</b></td>
				<td><input type="texte" size="20" maxlength="32" name="login"<?php
	if ($login != '')
		echo ' value="'.htmlspecialchars($login, ENT_QUOTES, _cst_encoding).'"';
	elseif (isset($account))
		echo ' value="'.htmlspecialchars($account['login'], ENT_QUOTES, _cst_encoding).'"';
				?> /></td>
			</tr>
			<tr>
				<td><b>Password:</b></td>
				<td><input type="password" size="20" maxlength="32" name="password"<?php
	if (isset($account))
		echo ' value="'.htmlspecialchars($account['password'], ENT_QUOTES, _cst_encoding).'"';
				?> /></td>
			</tr>
			<tr>
				<td><b>Password confirmation:</b></td>
				<td><input type="password" size="20" maxlength="32" name="password2"<?php
	if (isset($account))
		echo ' value="'.htmlspecialchars($account['password2'], ENT_QUOTES, _cst_encoding).'"';
				?> /></td>
			</tr>
			<tr>
				<td><b>Email:</b></td>
				<td><input type="text" size="32" maxlength="128" name="email"<?php
	if (isset($account))
		echo ' value="'.htmlspecialchars($account['email'], ENT_QUOTES, _cst_encoding).'"';
				?> /></td>
			</tr>
			<tr>
				<td><b>Phone:</b></td>
				<td><input type="text" size="40" maxlength="64" name="phone"<?php
	if (isset($account))
		echo ' value="'.htmlspecialchars($account['phone'], ENT_QUOTES, _cst_encoding).'"';
				?> /></td>
			</tr>
			<tr>
				<td><b>First Name:</b></td>
				<td><textarea name="firstname" cols="30" rows="3"><?php
	if (isset($account))
		echo htmlspecialchars($account['firstname'], ENT_QUOTES, _cst_encoding);
				?></textarea></td>
			</tr>
			<tr>
				<td><b>Last Name:</b></td>
				<td><textarea name="lastname" cols="30" rows="3"><?php
	if (isset($account))
		echo htmlspecialchars($account['firstname'], ENT_QUOTES, _cst_encoding);
				?></textarea></td>
			</tr>
			<tr>
				<td><b>Street:</b></td>
				<td><textarea name="addr_street" cols="30" rows="3"><?php
	if (isset($account))
		echo htmlspecialchars($account['addr_street'], ENT_QUOTES, _cst_encoding);
				?></textarea></td>
			</tr>
			<tr>
				<td><b>Street 2:</b></td>
				<td><textarea name="addr_street2" cols="30" rows="3"><?php
	if (isset($account))
		echo htmlspecialchars($account['addr_street2'], ENT_QUOTES, _cst_encoding);
				?></textarea></td>
			</tr>
			<tr>
				<td><b>Zip code:</b></td>
				<td><input type="text" size="20" maxlength="64" name="addr_zip"<?php
	if (isset($account))
		echo ' value="'.htmlspecialchars($account['addr_zip'], ENT_QUOTES, _cst_encoding).'"';
				?> /></td>
			</tr>
			<tr>
				<td><b>Town:</b></td>
				<td><input type="text" size="50" maxlength="64" name="addr_town"<?php
	if (isset($account))
		echo ' value="'.htmlspecialchars($account['addr_town'], ENT_QUOTES, _cst_encoding).'"';
				?> /></td>
			</tr>
			<tr>
				<td><b>State:</b></td>
				<td><input type="text" size="50" maxlength="128" name="addr_state"<?php
	if (isset($account))
		echo ' value="'.htmlspecialchars($account['addr_state'], ENT_QUOTES, _cst_encoding).'"';
				?> /></td>
			</tr>
			<tr>
				<td><b>Country:</b></td>
				<td>
					<select name="addr_country">
<?php
	if (isset($account))
		$addr_country = $account['addr_country'];

	$countries = file('country.txt');
	foreach ($countries as $country) {
		list ($code, $name) = explode (';', $country);
		$name = str_replace("\r\n", '', $name);
		echo '<option value="'.$name.'"'.($name == $addr_country?
			' selected="selected"':'').'>'.$name.'</option>'."\r\n";
	}
?>
					</select>
				</td>
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

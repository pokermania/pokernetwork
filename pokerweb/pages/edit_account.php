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

if(_post_string('submit')) {

  $account = array('name' => _post_string('name'),
                   'password2' => _post_string('password2'),
                   'password3' => _post_string('password3'),
                   'email' => _post_string('email'),
                   'firstname' => _post_string('firstname'),
                   'lastname' => _post_string('lastname'),
                   'addr_street' => _post_string('addr_street'),
                   'addr_street2' => _post_string('addr_street2'),
                   'addr_zip' => _post_string('addr_zip'),
                   'addr_town' => _post_string('addr_town'),
                   'addr_state' => _post_string('addr_state'),
                   'addr_country' => _post_string('addr_country'),
                   'phone' => _post_string('phone'));

  try {

    if($account['email'] == '')
      throw new Exception('Email is mandatory');

    if (strlen($account['password2']) > 0) {

      if (strtolower($account['password2']) != strtolower($account['password3']))
        throw new Exception('Password and confirmation must be the same.');
      $set_password = true;
      $new_password = $account['password2'];
    } else
      $set_password = false;

    $setAccountPacket =	array(
                              'type' => 'PacketPokerSetAccount', 
                              'name' => $account['name'], 
                              'email' => $account['email'],
                              'firstname' => $account['firstname'],
                              'lastname' => $account['lastname'],
                              'addr_street' => $account['addr_street'],
                              'addr_street2' => $account['addr_street2'],
                              'addr_zip' => $account['addr_zip'],
                              'addr_town' => $account['addr_town'],
                              'addr_state' => $account['addr_state'],
                              'addr_country' => $account['addr_country'],
                              'phone' => $account['phone']
                              );

    if ($set_password)
      $setAccountPacket['password'] = $new_password;

    if($_FILES['image']['name'])
      $poker->setPlayerImage($_FILES['image']['tmp_name'], $_FILES['image']['type']);

    $poker->send($setAccountPacket);

    header('Location: index.php?comment=Account%20information%20updated%20successfully');
    die();

  } catch(Exception $e) {
    $poker_error = $e->getMessage();
  }
} else {
  try {
    $account = $poker->getPersonalInfo();
    $serial = $account['serial'];
  } catch(Exception $e) {
    $poker_error = $e->getMessage();
  }
}

  hci_header();

  if($poker_error) {
    print "<h3>" . $poker_error . "</h3>";
  }

?>
 <!-- ACCOUNT INFORMATION FORM -->
	<form method="post" enctype="multipart/form-data">
		<table>
			<tr>
				<td></td>
				<td>Edit Account</td>
			</tr>
			<tr>
				<td><b>Login*:</b></td>
				<td><input type="hidden" id="name" name="name" value="<?php print $account['name'] ?>"><?php print $account['name'] ?></td>
			</tr>
			<tr>
				<td><b>New password*:</b></td>
				<td><input type="password" size="20" maxlength="32" id="password2" name="password2" /></td>
			</tr>
			<tr>
				<td><b>New Password confirmation*:</b></td>
				<td><input type="password" size="20" maxlength="32" id="password3" name="password3" /></td>
			</tr>
			<tr>
				<td><b>Email*:</b></td>
				<td><input type="text" size="32" maxlength="128" id="email" name="email" value="<?php print $account['email'] ?>" /></td>
			</tr>
			<tr>
				<td><b>Phone:</b></td>
				<td><input type="text" size="40" maxlength="64" id="phone" name="phone" value="<?php print $account['phone'] ?>" /></td>
			</tr>
			<tr>
				<td><b>First Name:</b></td>
				<td><textarea id="firstname" name="firstname" cols="30" rows="3"><?php print $account['firstname'] ?></textarea></td>
			</tr>
			<tr>
				<td><b>Last Name:</b></td>
				<td><textarea id="lastname" name="lastname" cols="30" rows="3"><?php print $account['lastname'] ?></textarea></td>
			</tr>
			<tr>
				<td><b>Street:</b></td>
				<td><textarea id="addr_street" name="addr_street" cols="30" rows="3"><?php print $account['addr_street'] ?></textarea></td>
			</tr>
			<tr>
				<td><b>Street 2:</b></td>
				<td><textarea id="addr_street2" name="addr_street2" cols="30" rows="3"><?php print $account['addr_street2'] ?></textarea></td>
			</tr>
			<tr>
				<td><b>Zip code:</b></td>
				<td><input type="text" size="20" maxlength="64" id="addr_zip" name="addr_zip" value="<?php print $account['addr_zip'] ?>" /></td>
			</tr>
			<tr>
				<td><b>Town:</b></td>
				<td><input type="text" size="50" maxlength="64" id="addr_town" name="addr_town" value="<?php print $account['addr_town'] ?>" /></td>
			</tr>
			<tr>
				<td><b>State:</b></td>
				<td><input type="text" size="50" maxlength="128" id="addr_state" name="addr_state" value="<?php print $account['addr_state'] ?>" /></td>
			</tr>
			<tr>
				<td><b>Country:</b></td>
				<td>
					<select id="addr_country" name="addr_country">
<?php

	$countries = file('country.txt');
	foreach ($countries as $country) {
		list ($code, $name) = explode (';', $country);
		$name = str_replace("\r\n", '', $name);
		echo '<option value="'.$name.'"'.($name == $account['addr_country']?
			' selected="selected"':'').'>'.$name.'</option>'."\r\n";
	}
?>
					</select>
				</td>
			</tr>
			<tr>
				<td></td>
				<td>
                                        <img src="image.php?serial=<? print $serial ?>" />
					<b>Avatar<sup>*</sup>: <input type="file" name="image"></b><br />
				<td></td>
				<td>
					<input type="submit" name='submit' value="Ok" />
				</td>
			</tr>
		</table>
	</form>
<?php
	hci_footer();
?>

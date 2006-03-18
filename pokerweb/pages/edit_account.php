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
  global $poker_error;
  global $poker;

  $user_name = _post_string('name');
  $password = _post_string('password');
  $password2 = _post_string('password2');
  $password3 = _post_string('password3');
  $email = _post_string('email');
  $addr_street = _post_string('addr_street');
  $addr_zip = _post_string('addr_zip');
  $addr_town = _post_string('addr_town');
  $addr_state = _post_string('addr_state');
  $addr_country = _post_string('addr_country');
  $phone = _post_string('phone');

  $del_avatar = _post_numeric('del_avatar', 0);

  if (strlen($password2) > 0) {

    if (strtolower($password2) != strtolower($password3)) {
      $poker_error = 'Password and confirmation must be the same.';
      return false;
    }

    $set_password = true;
    $new_password = $password2;
  } else
    $set_password = false;

  if ($del_avatar == 1) {
    $type_mime = '';
    $image = '';
  }

  if (isset($_FILES) && isset($_FILES['picture']) && $_FILES['picture']['size'] > 0) {
    require_once 'lib_images.php';
    list($type_mime, $image) = upload_avatar ('picture', _cookie_numeric('serial'));
  }

  $setAccountPacket =	array(
                              'type' => 'PacketPokerSetAccount', 
                              'name' => $user_name, 
                              'email' => $email,
                              'addr_street' => $addr_street,
                              'addr_zip' => $addr_zip,
                              'addr_town' => $addr_town,
                              'addr_state' => $addr_state,
                              'addr_country' => $addr_country,
                              'phone' => $phone
                              );

  if (isset($type_mime)) {
    $setAccountPacket['skin_image_type'] = $type_mime;
    $setAccountPacket['skin_image'] = new soapval ('skin_image', 'base64Binary', base64_encode($image));
  }

  if ($set_password)
    $setAccountPacket['password'] = $new_password;

  return $poker->send($setAccountPacket) != null;
}

if(_post_string('submit') && validate()) {
  header('Location: index.php?comment=Account%20information%20updated%20successfully');
  die();
}

$PacketPokerPersonalInfo = $poker->getPersonalInfo();

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
				<td><b>Login:</b></td>
				<td>
          <?php if ($PacketPokerPersonalInfo != false) echo $PacketPokerPersonalInfo['name']; ?>
          <input type="hidden" name="name" value="<?php echo $PacketPokerPersonalInfo['name']; ?>" />
        </td>
			</tr>
			<tr>
				<td><b>Actual password:</b></td>
				<td><input type="password" size="20" maxlength="32" name="password"<?php
	if (isset($account))
		echo ' value="'.htmlspecialchars($account['password'], ENT_QUOTES, _cst_encodage).'"';
				?> /></td>
			</tr>
			<tr>
				<td><b>New password:</b></td>
				<td><input type="password" size="20" maxlength="32" name="password2"<?php
	if (isset($account))
		echo ' value="'.htmlspecialchars($account['password2'], ENT_QUOTES, _cst_encodage).'"';
				?> /></td>
			</tr>
			<tr>
				<td><b>New password confirmation:</b></td>
				<td><input type="password" size="20" maxlength="32" name="password3"<?php
	if (isset($account))
		echo ' value="'.htmlspecialchars($account['password3'], ENT_QUOTES, _cst_encodage).'"';
				?> /></td>
			</tr>
			<tr>
				<td><b>Email:</b></td>
				<td><input type="text" size="32" maxlength="128" name="email" value="<?php
	if (isset($account))
		echo htmlspecialchars($account['email'], ENT_QUOTES, _cst_encodage);
	elseif ($PacketPokerPersonalInfo != false) 
		echo $PacketPokerPersonalInfo['email']; ?>" /></td>
			</tr>
			<tr>
				<td><b>Phone:</b></td>
				<td><input type="text" size="40" maxlength="64" name="phone" value="<?php
	if (isset($account))
		echo htmlspecialchars($account['phone'], ENT_QUOTES, _cst_encodage);
	elseif ($PacketPokerPersonalInfo != false) 
		echo $PacketPokerPersonalInfo['phone']; ?>" /></td>
			</tr>
			<tr>
				<td><b>Street:</b></td>
				<td><textarea name="addr_street" cols="40" rows="4"><?php
	if (isset($account))
		echo htmlspecialchars($account['addr_street'], ENT_QUOTES, _cst_encodage);
	elseif ($PacketPokerPersonalInfo != false) 
		echo $PacketPokerPersonalInfo['addr_street']; ?></textarea></td>
			</tr>
			<tr>
				<td><b>Zip code:</b></td>
				<td><input type="text" size="20" maxlength="64" name="addr_zip" value="<?php
	if (isset($account))
		echo htmlspecialchars($account['addr_zip'], ENT_QUOTES, _cst_encodage);
	elseif ($PacketPokerPersonalInfo != false) 
		echo $PacketPokerPersonalInfo['addr_zip']; ?>" /></td>
			</tr>
			<tr>
				<td><b>Town:</b></td>
				<td><input type="text" size="50" maxlength="64" name="addr_town" value="<?php
	if (isset($account))
		echo htmlspecialchars($account['addr_town'], ENT_QUOTES, _cst_encodage);
	elseif ($PacketPokerPersonalInfo != false) 
		echo $PacketPokerPersonalInfo['addr_town']; ?>" /></td>
			</tr>
			<tr>
				<td><b>State:</b></td>
				<td><input type="text" size="50" maxlength="128" name="addr_state" value="<?php
	if (isset($account))
		echo htmlspecialchars($account['addr_state'], ENT_QUOTES, _cst_encodage);
	elseif ($PacketPokerPersonalInfo != false) 
		echo $PacketPokerPersonalInfo['addr_state']; ?>" /></td>
			</tr>
			<tr>
				<td><b>Country:</b></td>
				<td>
				
					<select name="addr_country">
<?php
	if (isset($account))
		$addr_country = htmlspecialchars($account['addr_country'], ENT_QUOTES, _cst_encodage);
	elseif ($PacketPokerPersonalInfo != false)
		$addr_country = $PacketPokerPersonalInfo['addr_country'];

	$countries = file('country.txt');
	foreach ($countries as $country) {
		list ($code, $name) = explode (';', $country);
		echo '<option value="'.$name.'"'.($country == $addr_country?
			' selected="selected"':'').'>'.$name.'</option>'."\r\n";
	}
?>
					</select>
				</td>
			</tr>
			<tr>
				<td></td>
				<td>
					<b>Avatar<sup>*</sup>:</b><br />
<?php
	if (true) { //$avatar != ''
?>
					
					<input type="checkbox" name="del_avatar" value="1" /> Delete avatar.<br />
<?php
	}
?>
				</td>
			</tr>
			<tr>
				<td></td>
				<td>
					<input type="file" name="picture" /><br />
<?php 
	echo '<sup>*</sup>Avatar limits: '._cst_avatar_max_width.'x'.
		_cst_avatar_max_height.', Size in KB: '.(_cst_avatar_max_size / 1024);
?>
				</td>
			</tr>
			<tr>
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

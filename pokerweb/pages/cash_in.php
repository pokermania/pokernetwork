<?php
//
// Copyright (C) 2006, 2007 Loic Dachary <loic@dachary.org>
// Copyright (C) 2006 Mekensleep
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
//

require_once 'common.php';

if(!($user_info = $poker->isLoggedin())) {
  no_auth_handler(_get_string('name'), $_SERVER['REQUEST_URI']);
}

if(_post_string('submit')) {
  try {
    $amount = _post_string('amount');

    if($amount == '' or $amount < 0)
      throw new Exception("amount must be greater than zero");
    
    $currency_url = dirname(_me()) . "/currency_one.php";
    $handle = fopen($currency_url . "?command=get_note&autocommit=yes&value=" . $amount, "r");
    if(!$handle)
      throw new Exception($currency_url . " request failed, check the server logs");

    $lines = array();
    while($line = fgets($handle)) {
      array_push($lines, $line);
    }
    fclose($handle);

    $note = split("\t", rtrim($lines[0]));

    if(count($lines) < 1)
      throw new Exception("currency server returned nothing");

    if(count($note) != 4 || !is_numeric($note[1]) || !is_numeric($note[3]) || (intval($note[3]) != intval($amount))) {
      error_log(print_r($lines, true));
      throw new Exception("currency server returned an invalid answer");
    }

    $poker->cashIn($note);

    header('Location: index.php?comment=Cash%20in%20was%20successful');
    die();
  } catch(Exception $error) {
    $poker_error = $error->getMessage();
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
				<td>Cash-In</td>
			</tr>
			<tr>
				<td><b>Amount:</b></td>
				<td>
          <input type="text" name="amount" value="<?php echo $amount; ?>" />
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

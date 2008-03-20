<?php
//
// Copyright (C) 2006, 2007, 2008 Loic Dachary <loic@dachary.org>
// Copyright (C) 2006 Mekensleep
//
// Mekensleep
// 24 rue vieille du temple
// 75004 Paris
//       licensing@mekensleep.com
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 3 of the License, or
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

    if(!is_numeric($amount))
      throw new Exception("amount must be numeric");
    
    if($amount == '' or $amount < 0)
      throw new Exception("amount must be greater than zero");

    $amount *= 100;
    
    $currency_one_public = ereg("^http", _cst_currency_one_public) ? _cst_currency_one_public : (dirname(_me()) . "/" . _cst_currency_one_public);
    $currency_one_private = ereg("^http", _cst_currency_one_private) ? _cst_currency_one_private : (dirname(_me()) . "/" . _cst_currency_one_private);

    if(isset($_POST['currency']) && $_POST['currency'] != '')
      $currency =  $_POST['currency'];

    $url = $currency_one_public . "?command=get_note&autocommit=yes&value=" . $amount;
    if(isset($currency))
      $url .= "&id=" . $currency;

    $handle = fopen($url, "r");
    if(!$handle)
      throw new Exception($currency_one_public . " request failed, check the server logs");

    $lines = array();
    while($line = fgets($handle)) {
      array_push($lines, $line);
    }
    fclose($handle);

    $note = split("\t", rtrim($lines[0]));

    if(count($lines) < 1)
      throw new Exception("currency server returned nothing");

    $note[0] = $currency_one_private;

    if(count($note) != 4 || !is_numeric($note[1]) || !is_numeric($note[3]) || (intval($note[3]) != intval($amount))) {
      error_log(print_r($lines, true));
      throw new Exception("currency server returned an invalid answer");
    }

    $poker->cashIn($note, $currency);

    header('Location: index.php?comment=Cash%20in%20was%20successful');
    die();
  } catch(Exception $error) {
    $poker_error = $error->getMessage();
  }
} else {
  $currency = 1;
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
				<td><? echo _('Cash-In') ?></td>
			</tr>
			<tr>
				<td><b><? echo _('Amount') ?>:</b></td>
				<td>
          <input type="text" name="amount" value="<?php echo $amount; ?>" />
        </td>
			</tr>
			<tr>
				<td><b><? echo _('Currency') ?>:</b></td>
				<td>
          <input type="text" name="currency" value="<?php echo $currency; ?>" />
        </td>
			</tr>
			<tr>
				<td></td>
				<td>
					<input type="submit" name='submit' value="<? echo _('Ok') ?>" />
				</td>
			</tr>
		</table>
	</form>
<?php

hci_footer();

?>

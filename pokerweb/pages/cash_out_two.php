<?php
//
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

function validate() {
  global $poker_error;
  global $poker;
  global $amount, $net_account, $secure_id;

  $amount = _post_string('amount');
  $secure_id = _post_string('secure_id');
  $net_account = _post_string('net_account');

  if($amount == '' or $amount < 0) {
    $poker_error = "amount must be greater than zero";
    return false;
  }

  return true;
}

function action() {
  global $poker;
  global $poker_error;
  global $amount, $net_account, $secure_id;
  global $note;

  $currency_url = dirname(_me()) . "/currency_two.php";

  try {
    $packet = $poker->cashOut($currency_url, $amount);
    $poker->cashOutCommit($packet['name']);

    $poker_error .= "Pass cashOutCommit ";

    $cmd = "/usr/bin/python neteller.py --dry-run --php --option 'currency=USD&net_account=" . $net_account . "&secure_id=" . $secure_id . "&amount=" . $amount . "&merch_transid=1234' out";
    $poker_error .= "neteller command " . $cmd;
    $handle = popen($cmd, "r");
    $buffer = '';
    if ($handle) {
      while (!feof($handle)) {
        $buffer .= fread($handle, 4096);
      }
      pclose($handle);
    }
    $poker_error .= "buffer " . $buffer;

    eval('$in=' . $buffer);

    if(!isset($in) or $in == '') {
      $poker_error .= "eval failed";
      return false;
    }

    if(isset($in['error'])) {
      $poker_error .= "ERROR " . $in['error'] . "\n";
      return false;
    }

    $handle = fopen($currency_url . "?command=put_note&serial=" . $packet['bserial'] . "&name=" . $packet['name'] . "&value=" . $packet['value'], "r");
    $line = fgets($handle);
    $poker_error .= "put_note $line";
    fclose($handle);

    return true;
  } catch(Exception $error) {
    $poker_error = "Unexpected error " . $error;
    return false;
  }
}

if(_post_string('submit') && validate() && action()) {
  header('Location: index.php?comment=Cash%20out%20was%20successful');
  die();
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
				<td>Cash-Out</td>
			</tr>
			<tr>
				<td><b>Amount:</b></td>
				<td>
                                     <input type="text" name="amount" value="<?php echo $amount; ?>" />
                               </td>
			</tr>
			<tr>
				<td><b>Neteller Account:</b></td>
				<td>
                                     <input type="text" name="net_account" value="<?php echo $net_account; ?>" />
                               </td>
			</tr>
			<tr>
				<td><b>Secure Id:</b></td>
				<td>
                                     <input type="text" name="secure_id" value="<?php echo $secure_id; ?>" />
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

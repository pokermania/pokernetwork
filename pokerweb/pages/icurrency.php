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

if(getenv('LOCAL_PHP_PATH'))
  {
    define('CURRENCY_INCLUDED', 'no');
    ini_set('include_path', ini_get('include_path') . ":" . getenv('LOCAL_PHP_PATH'));
    parse_str(getenv('QUERY_STRING'), $_GET);
  }

require_once 'currency_configuration.php';
require_once 'currency.php';

if(getenv('LOCAL_PHP_PATH'))
  {
    $GLOBALS['currency_db_base'] = 'currencytest';
  }

function main() {
  try {
    $page = array();
    $currency = new currency($GLOBALS['currency_db_base'], $GLOBALS['currency_db_user'], $GLOBALS['currency_db_password']);

    if($_GET['command'] == 'get_note') {
      if(isset($_GET['count'])) $count = $_GET['count'];
      else $count = 1;
      for($i = 0; $i < $count; $i++) {
        $note = $currency->get_note($_GET['value']);
        array_push($page, join("\t", $note));
      }
    } elseif($_GET['command'] == 'merge_notes') {
      if(isset($_GET['values'])) {
        if($_GET['values'] == '') $_GET['values'] = array();
      } else {
        $_GET['values'] = FALSE;
      }
      $notes = $currency->merge_notes_columns($_GET['serial'], $_GET['name'], $_GET['value'], $_GET['values']);
      foreach ($notes as $note)
        array_push($page, join("\t", $note));
    } elseif($_GET['command'] == 'change_note') {
      $note = $currency->change_note($_GET['serial'], $_GET['name'], $_GET['value']);
      array_push($page, join("\t", $note));
    } else {
      throw new Exception("unknow command " . $_GET['command']);
    }

    print join("\n", $page);
    $status = true;
  } catch(Exception $error) {
    ob_end_flush();
    print $error->getMessage();
    $status = false;
  }
  return $status;
}

if(CURRENCY_INCLUDED != 'yes') {
  ob_start();
  $status = main();
  if(!getenv('LOCAL_PHP_PATH')) {
    if($status) {
      header('Content-type: text/plain');
    } else {
      header('HTTP/1.0 500 Internal Server Error');
    }
  }
  ob_end_flush();
}

?>

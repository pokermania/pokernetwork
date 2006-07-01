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

$GLOBALS['bank_db_persist'] = TRUE;
$GLOBALS['bank_db_host'] = "localhost";
$GLOBALS['bank_db_port'] = 3306;
$GLOBALS['bank_db_base'] = "bank";
$GLOBALS['bank_db_user'] = "bank";
$GLOBALS['bank_db_password'] = "bank";

$GLOBALS['bank_random'] = "/dev/urandom";

$GLOBALS['bank_url'] = "http://localhost/bank/";

$GLOBALS['bank_values'] = array(1, 2, 5,
                                10, 20, 50,
                                100, 200, 500,
                                1000, 2000, 5000,
                                10000, 20000, 50000,
                                100000, 200000, 500000,
                                1000000, 2000000, 5000000,
                                10000000, 20000000, 50000000,
                                100000000, 200000000, 500000000,
                                1000000000, 2000000000, 5000000000,
                                10000000000, 20000000000, 50000000000,
                                100000000000, 200000000000, 50000000000,
                                1000000000000, 2000000000000, 500000000000);

?>

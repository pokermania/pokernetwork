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
//
	function upload_error ($code) {
		switch ($code) {
			case UPLOAD_ERR_OK:
				break;
			case UPLOAD_ERR_INI_SIZE:
				quit('File size over php.ini limitation.');
				break;
			case UPLOAD_ERR_FORM_SIZE:
				quit('File size over form limitation.');
				break;
			case UPLOAD_ERR_PARTIAL:
				quit('File partialy downloaded.');
				break;
			case UPLOAD_ERR_NO_FILE:
				quit('No file uploaded.');
				break;
		}
	}

	function upload_avatar ($nom_champ, $serial) {
		if (!isset($_FILES[$nom_champ]))
			quit('No file posted.');

		if ($_FILES[$nom_champ]['size'] == 0)
			quit('File size null.');

		if ($_FILES[$nom_champ]['size'] > _cst_avatar_max_size)
			quit('File\'s size over the limit of '._cst_avatar_max_size.'KB');

		if ($_FILES[$nom_champ]['error'] != 0)
			upload_error($_FILES[$nom_champ]['error']);

		$tmp_name = $_FILES[$nom_champ]['tmp_name'];

		$tab = explode('.', $tmp_name);
		$ext = strtolower($tab[count($tab) - 1]);

		switch ($ext) {
			case 'gif':
				$src_img = ImageCreateFromGif($tmp_name);
				$type_mime = 'image/gif';
				break;
			case 'jpeg':
			case 'jpg':
				$src_img = imagecreatefromjpeg($tmp_name);
				$type_mime = 'image/jpeg';
				break;
			case 'png':
				$src_img = ImageCreateFromPng($tmp_name);
				$type_mime = 'image/png';
				break;
			default:
				quit('Unknown file format: "'.$ext.'"');
		}

		$image_src_w = imagesx($src_img);
		$image_src_h = imagesy($src_img);

		if ($image_src_w < 1 || $image_src_w > _cst_avatar_max_width)
			quit('Invalid width.');

		if ($image_src_h < 1 || $image_src_h > _cst_avatar_max_height)
			quit('Invalid heigh.');

		$image = file_get_contents($tmp_name);

		return array($type_mime, $image);
	}
?>

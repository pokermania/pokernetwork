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
// To get a full nusoap debug trace :    
//    print "<pre>" . htmlspecialchars($this->client->getDebug()) . "</pre>";
//

if(!class_exists('nusoapclient')) {
  require_once 'nusoap.php';
}

require_once 'birthday.php';

class poker {

  const E_UNKNOWN		=	0;
  const E_IMAGE_LOGIN		=	1;
  const E_IMAGE_ACK		=	2;
  const E_IMAGE_SET		=	3;
  const E_LOGIN_FAILED		=	4;
  const E_LOGIN_SERIAL		=	5;
  const E_LOGIN_UNKNOWN		=	6;
  const E_SEND_AUTH_REQUEST	=	7;
  const E_SEND_SOAP_BROKEN	=	8;
  const E_SEND_SERIAL_MISMATCH  =	9;
  const E_SEND_FATAL_SOAP_ERROR	=      10;
  const E_SEND_CALL_SOAP_ERROR	=      11;
  const E_SEND_SERVER_ERROR	=      12;
  const E_SEND_REPLY_NO_TYPE	=      13;
  const E_SEND_UNKNOWN		=      14;
  const E_PERSONAL_INFO_ANSWER	=      15;
  const E_CASH_IN_INFO_ANSWER	=      16;
  const E_CASH_OUT_INFO_ANSWER	=      17;
  const E_CASH_OUT_COMMIT	=      18;
  const E_CONNECT_SOAP_BROKEN	=      19;

  function poker($host) {
    $this->connect($host);
    $this->no_auth_handler = null;
    $this->timeout_cookie = 0;
    $this->serial = null;
    $this->twisted_session = null;
    $this->verbose = 0;
  }

  function setTimeoutCookie($timeout_cookie) {
    $this->timeout_cookie = $timeout_cookie;
  }

  function setNoAuthHandler($no_auth_handler) {
    $this->no_auth_handler = $no_auth_handler;
  }

  function connect($host) {
    $this->client = new nusoapclient($host);
  }

  function login($login, $password) {
    $packets = $this->send(array('type' => 'PacketLogin', 
                                 'password' => $password, 
                                 'name' => $login));

    if($packets) {
      switch ($packets[0]['type']) {
      case 'PacketAuthRefused':
        throw new Exception(_('Authentication failed').", " . _($packets[0]['message']), self::E_LOGIN_FAILED);
        break;
      case 'PacketAuthOk':
        if($packets[1]['type'] == 'PacketSerial') {
          setcookie('serial', $packets[1]['serial'], $this->timeout_cookie, '/');
	  $this->serial = $packets[1]['serial'];
        } else
          throw new Exception('Empty or missing PacketSerial.', self::E_LOGIN_SERIAL);
        break;
      default:
        throw new Exception('Unknown Packet type ' . $packets[0]['type'], self::E_LOGIN_UNKNOWN);
        break;
      }
    }
  }

  function logout() {
    setcookie('serial', FALSE, time() - 3600, '/');
    setcookie('TWISTED_SESSION', FALSE, time() - 3600, '/');
    $this->serial = null;
    $this->twisted_session = null;
  }

  function getPersonalInfo() {
    $packets = $this->send(array('type' => 'PacketPokerGetPersonalInfo'));
    if($packets) {
      if($packets[0]['type'] == 'PacketPokerPersonalInfo') {
        $packet = $packets[0];
        $birthday = new birthday(strtotime($packet['birthdate']));
        $packet['birthdate'] = $birthday;
        $packet['birthday'] = $birthday->day;
        $packet['birthmonth'] = $birthday->month;
        $packet['birthyear'] = $birthday->year;
        return  $packet;
      } else {
        throw new Exception('Expected PacketPokerPersonalInfo but got ' . $packets[0]['type'], self::E_PERSONAL_INFO_ANSWER);
      }
    }
  }

  function cashIn($note, $id) {
    if(isset($id) && $id != '')
      $url = $note[0] . "?id=" . $id;
    else
      $url = $note[0];
    $packets = $this->send(array('type' => 'PacketPokerCashIn',
                                 'url' => $url,
                                 'bserial' => intval($note[1]),
                                 'name' => $note[2],
                                 'value' => intval($note[3])));
    if($packets[0]['type'] == 'PacketAck') {
      return $packets[0];
    } else
      throw new Exception('Expected PacketAck but got ' . $packets[0]['type'], self::E_CASH_IN_INFO_ANSWER);
  }

  function cashOut($url, $value, $id) {
    if(isset($id) && $id != '')
      $url .= "?id=" . $id;
    $packets = $this->send(array('type' => 'PacketPokerCashOut',
                                 'url' => $url,
                                 'value' => $value));
    if($packets[0]['type'] == 'PacketPokerCashOut') {
      return $packets[0];
    } else
      throw new Exception('Expected PacketPokerCashOut but got ' . $packets[0]['type'], self::E_CASH_OUT_INFO_ANSWER);
  }

  function cashOutCommit($transaction_id) {
    $packets = $this->send(array('type' => 'PacketPokerCashOutCommit',
                                 'transaction_id' => $transaction_id));
    if($packets[0]['type'] == 'PacketAck') {
      return $packets[0];
    } else {
      throw new Exception('Expected PacketAck but got ' . $packets[0]['type'], self::E_CASH_OUT_COMMIT);
    }
  }

  function serialIsSet() {
    return $this->serial || isset($_COOKIE['serial']);
  }

  //
  // global $_FILES;
  // setPlayerImage($_FILES['tmp_name'], $_FILES['type'])
  //
  function setPlayerImage($image_file, $image_type, $maxWidth = 100, $maxHeight = 100) {
    
    if(!$this->serialIsSet())
      throw new Exception("Poker::setPlayerImage must be called after login", self::E_IMAGE_LOGIN);

    if( eregi( "jpeg", $image_type) ) // JPG
      $type = "JPG";
    elseif( eregi( "png", $image_type ) ) // PNG
      $type = "PNG";

		
    $picInfos = getimagesize( $image_file );
		
    $width = $picInfos[0];
    $height = $picInfos[1];
		
    if( $width > $maxWidth & $height <= $maxHeight )
      {
        $ratio = $maxWidth / $width;
      }
    elseif( $height > $maxHeight & $width <= $maxWidth )
      {
        $ratio = $maxHeight / $height;
      }
    elseif( $width > $maxWidth & $height > $maxHeight )
      {
        $ratio1 = $maxWidth / $width;
        $ratio2 = $maxHeight / $height;
        $ratio = ($ratio1 < $ratio2)? $ratio1:$ratio2;
      }
    else
      {
        $ratio = 1;
      }

    $nWidth = floor($width*$ratio);
    $nHeight = floor($height*$ratio);
		
    if( $type == 'JPG' )
      $origPic = imagecreatefromjpeg( $image_file );
    elseif( $type == 'PNG' )
      $origPic = imagecreatefrompng( $image_file );
			
    $New = ImageCreate($nWidth,$nHeight);
    ImageCopyResized($New, $origPic, 0, 0, 0, 0, $nWidth, $nHeight, $width, $height);

    $tmp_file = tempnam("/tmp", "poker");
    imagepng($New, $tmp_file);
    $image = file_get_contents($tmp_file);
    unlink($tmp_file);

    $image_base64 = base64_encode($image);

    $packets = $this->send(array('type' => 'PacketPokerPlayerImage',
                                 'serial' => $this->serial,
                                 'image' => $image_base64,
                                 'image_type' => 'image/png'));
    if($packets[0]['type'] == 'PacketAck') {
      return true;
    } else {
      throw new Exception('Expected PacketAck but got ' . $packets[0]['type'], self::E_IMAGE_ACK);
    }
  }

  function getPlayerImage($serial) {
    $packets = $this->send(array('type' => 'PacketPokerGetPlayerImage',
                                 'serial' => $serial));
    if($packets[0]['type'] == 'PacketPokerPlayerImage') {
      $image = $packets[0]['image'];
      if($image != '')
        return imagecreatefromstring(base64_decode($image));
      else
        return '';
    } else {
      throw new Exception('Expected PacketPokerPlayerImage but got ' . $packets[0]['type'], self::E_IMAGE_SET);
    }
  }

  function isLoggedIn() {
    $packets = $this->sendNoAuth(array('type' => 'PacketPokerGetPersonalInfo'));
    if($packets[0]['type'] == 'PacketPokerPersonalInfo')
      return $packets[0];
    else
      return false;
  }

  function sendNoAuth($packet) {

    if($this->verbose > 0) error_log("sendNoAuth");

    $err = $this->client->getError();
    if ($err)
      throw new Exception($err, self::E_SEND_SOAP_BROKEN);

    if (isset($this->serial))
      $cookie_serial = $this->serial;
    else
      $cookie_serial = $_COOKIE['serial'];
    $param_serial = $_GET['serial'];

    //
    // If a serial was provided in the parameters and there is a different
    // serial in the cookie, clear the cookie and start over.
    //
    if($param_serial && $cookie_serial && $param_serial != $cookie_serial) {
      $this->logout();
      if(isset($this->no_auth_handler)) {
        call_user_func($this->no_auth_handler, $_GET['name'], $_SERVER['REQUEST_URI']);
        return;
      } else {
        throw new Exception('serial param_serial = ' . $param_serial . ' and cookie_serial = ' . $cookie_serial . ' are different and no handler was set by setNoAuthHandler', self::E_SEND_SERIAL_MISMATCH);
      }
    }

    //
    // Set the packet serial from the corresponding cookie, if
    // available.  If the packet does not make user of the serial
    // field it won't harm to have one.
    //
    if($cookie_serial) {
      $packet['serial'] = intval($cookie_serial);
    } else {
      $packet['serial'] = 0;
    }

    //
    // Set the session cookie to be used over the SOAP call, if any
    //
    if (isset($this->twisted_session))
      $twisted_session = $this->twisted_session;
    else
      $twisted_session = $_COOKIE['TWISTED_SESSION'];
    if($twisted_session) {
      $this->client->cookies[] = array('name' => 'TWISTED_SESSION',
                                       'value' => $twisted_session,
                                       'path' => '/',
                                       'domain' => '',
                                       'secure' => false);
    }
    $result = $this->client->call('handlePacket', array('use sessions', $packet));
    if ($this->client->fault) {
      throw new Exception('Error during soap call.', self::E_SEND_FATAL_SOAP_ERROR);
    } else {
      $err = $this->client->getError();
      if ($err) {
        throw new Exception($err, self::E_SEND_CALL_SOAP_ERROR);
      } else {
        foreach ($result as $packet) {
          if(isset($packet['type'])) {
            switch ($packet['type']) {
            case 'PacketError':
            case 'PacketPokerError':
              //
              // Fatal error from which we can't recover. 
              //
              throw new Exception('type = ' . $packet['other_type'] . ', code = ' . $packet['code'] . ', message = ' . $packet['message'], self::E_SEND_SERVER_ERROR);
              break;
            default:
              break;
            }
          } else
            throw new Exception('Packet without type.', self::E_SEND_REPLY_NO_TYPE);
        }
        //
        // Set or reset the twisted session cookie.
        //
        $cookie = $this->client->cookies[0];
        if($twisted_session != $cookie['value']) {
          setcookie($cookie['name'], $cookie['value'], $this->timeout_cookie, '/');
	  if ($cookie['name'] == 'TWISTED_SESSION')
	    $this->twisted_session = $cookie['value'];
        }
        return $result;
      }
    }
  }

  function send($packet) {

    $packets = $this->sendNoAuth($packet);

    if($packets) {
      foreach ($packets as $packet) {
        if($packet['type'] == 'PacketAuthRequest') {
          if(isset($this->no_auth_handler)) {
            call_user_func($this->no_auth_handler, $_GET['name'], $_SERVER['REQUEST_URI']);
            return;
          }
          throw new Exception('Sending ' . $packet['type'] . ' packet requires authentification and no handler was set by setNoAuthHandler', self::E_SEND_AUTH_REQUEST);
        }
      }
    }

    return $packets;
  }

}

?>
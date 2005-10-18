<?php

require_once 'lib_filters.php';
require_once 'nusoap.php';

class poker {

  function poker($host) {
    $this->connect($host);
    $this->error_handler = null;
    $this->no_auth_handler = null;
    $this->timeout_cookie = 0;
    $this->serial = null;
    $this->twisted_session = null;
  }

  function setErrorHandler($error_handler) {
    $this->error_handler = $error_handler;
  }

  function setTimeoutCookie($timeout_cookie) {
    $this->timeout_cookie = $timeout_cookie;
  }

  function setNoAuthHandler($no_auth_handler) {
    $this->no_auth_handler = $no_auth_handler;
  }

  function error($type, $code, $message) {
    if(isset($this->error_handler)) {
      call_user_func($this->error_handler, $type, $code, $message);
    }
    return null;
  }

  function connect($host) {
    $this->client = new soapclient($host);
  }

  function login($login, $password) {
    $result = false;
    $packets = $this->send(array('type' => 'PacketLogin', 
                                 'password' => $password, 
                                 'name' => $login));

    if($packets) {
      switch ($packets[0]['type']) {
      case 'PacketAuthRefused':
        return $this->error(6, 0, 'Authentication failed, ' . $packets[0]['string']);
        break;
      case 'PacketAuthOk':
        if($packets[1]['type'] == 'PacketSerial') {
          setcookie('serial', $packets[1]['serial'], $this->timeout_cookie, '/');
	  $this->serial = $packets[1]['serial'];
          $result = true;
        } else
          return $this->error(1000, 0, 'Empty or missing PacketSerial.');
        break;
      default:
        return $this->error(0, 0, 'Unknown Packet type ' . $packets[0]['type']);
      }
    }

    return $result;
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
        return $packets[0];
      } else {
        return $this->error(1000, 1, 'Expected PacketPokerPersonalInfo but got ' . $packets[0]['type']);
      }
    } else {
      return $packets;
    }
  }

  function isLoggedIn() {
    $packets = $this->sendNoAuth(array('type' => 'PacketPokerGetPersonalInfo'));
    if($packets) {
      return $packets[0]['type'] == 'PacketPokerPersonalInfo';
    } else {
      return $packets;
    }
  }

  function sendNoAuth($packet) {

    $err = $this->client->getError();
    if ($err) {
      return $this->error(1000, 2, $err);
    }

    if (isset($this->serial))
      $cookie_serial = $this->serial;
    else
      $cookie_serial = _cookie_numeric('serial');
    $param_serial = _get_numeric('serial');

    //
    // If a serial was provided in the parameters and there is a different
    // serial in the cookie, clear the cookie and start over.
    //
    if($param_serial && $cookie_serial && $param_serial != $cookie_serial) {
      $this->logout();
      header('Location: ?name=' . _get_string('name'));
      die();
    }

    //
    // Set the packet serial from the corresponding cookie, if available.
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
      $twisted_session = _cookie_string('TWISTED_SESSION');
    if($twisted_session) {
      $this->client->cookies[] = array('name' => 'TWISTED_SESSION',
                                 'value' => $twisted_session,
                                 'path' => '/',
                                 'domain' => '',
                                 'secure' => false);
    }
    $result = $this->client->call('handlePacket', array('use sessions', $packet));
    if ($this->client->fault) {
      return $this->error(1000, 3, 'Error during soap call.');
    } else {
      $err = $this->client->getError();
      if ($err) {
        return $this->error(1000, 4, $err);
      } else {
        foreach ($result as $packet) {
          if(isset($packet['type'])) {
            switch ($packet['type']) {
            case 'PacketError':
            case 'PacketPokerError':
              //
              // Fatal error from which we can't recover. 
              //
              return $this->error($packet['other_type'], $packet['code'], $packet['message']);
              break;
            }
          } else {
            return $this->error(0, 0, 'Packet without type.');
          }
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
            call_user_func($this->no_auth_handler, _get_string('name'), $_SERVER['REQUEST_URI']);
          }
          return null;
        }
      }
    }
    return $packets;
  }
}

?>
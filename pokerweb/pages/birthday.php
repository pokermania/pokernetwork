<?php
  //
  // Copyright (C) 2007, 2008, 2009 Loic Dachary <loic@dachary.org>
  //
  // This software's license gives you freedom; you can copy, convey,
  // propagate, redistribute and/or modify this program under the terms of
  // the GNU Affero General Public License (AGPL) as published by the Free
  // Software Foundation (FSF), either version 3 of the License, or (at your
  // option) any later version of the AGPL published by the FSF.
  //
  // This program is distributed in the hope that it will be useful, but
  // WITHOUT ANY WARRANTY; without even the implied warranty of
  // MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero
  // General Public License for more details.
  //
  // You should have received a copy of the GNU Affero General Public License
  // along with this program in a file in the toplevel directory called
  // "AGPLv3".  If not, see <http://www.gnu.org/licenses/>.

class birthday {

  function birthday($birthday = null) {
    if(isset($birthday) && $birthday != '') {
      $this->set($birthday);
    } else {
      $this->day = $this->get_field('birthday');
      $this->month = $this->get_field('birthmonth');
      $this->year = $this->get_field('birthyear');
    }
    $this->verbose = 0;
  }

  function set($birthday) {
    if(is_int($birthday)) {
      $this->day = date('j', $birthday);
      $this->month = date('n', $birthday);
      $this->year = date('Y', $birthday);
    }
  }

  function as_string() {
    if($this->year != '' && $this->month != '' && $this->day != '')
      return $this->year . '-' . $this->month . '-' . $this->day;
    else
      return '';
  }

  function form() {
    $html = $this->form_day();
    $html .= " - " . $this->form_month();
    $html .= " - " . $this->form_year();
    return $html;
  }

  function form_day() {
    $html = '<select id="birthday" name="birthday">';
    for($i = 1; $i <= 31; $i++) {
      $html .= '<option value="'.$i.'"';
      if($this->day == $i) $html .= ' selected="selected"';
      $html .= '>'.$i.'</option>';
    }
    $html .= "</select>\r\n";
    return $html;
  }

  function form_month() {
    $html = '<select id="birthmonth" name="birthmonth">';
    for($i = 1; $i <= 12; $i++) {
      $html .= '<option value="'.$i.'"';
      if($this->month == $i) $html .= ' selected="selected"';
      $html .= '>'.strftime('%B', mktime(0, 0, 0, $i, 1, 1965)).'</option>';
    }
    $html .= "</select>\r\n";
    return $html;
  }

  function form_year() {
    $html = '<select id="birthyear" name="birthyear">';
    for($i = date('Y') - 10; $i > date('Y') - 100; $i--) {
      $html .= '<option value="'.$i.'"';
      if($this->year == $i) $html .= ' selected="selected"';
      $html .= '>'.$i.'</option>';
    }
    $html .= "</select>\r\n";
    return $html;
  }

  function get_field($field, $default = null) {
    $value = isset($_POST[$field]) && is_numeric($_POST[$field]) ? $_POST[$field] : "";
    if($value == "")
      $value = isset($_GET[$field]) && is_numeric($_GET[$field]) ? $_GET[$field] : "";
    return $value;
  }

  }

?>

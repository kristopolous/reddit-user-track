<?php
$_db = 'rating.json';

function db($key = false, $value = false) {
  global $_db;
  $db = [];
  if(file_exists($_db)) {
    $db = json_decode(file_get_contents($_db), true);
    if(!$db) {
      $db = [];
    }
  }

  switch(func_num_args()) {
    case 0: return $db; break;
    case 1: return isset($_db[$key]) ? $_db[$key] : null; break;
    case 2:
      $db[$key] = $value;
      file_put_contents($_db, json_encode($db));
      break;
  }
}


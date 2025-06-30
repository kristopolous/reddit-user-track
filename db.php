<?php

function db($key = false, $value = false) {
  $redis = new Redis();
  $redis->connect('127.0.0.1', 6379);
  $obj = 'rating';
  $db = $redis->hgetall($obj) ?? [];

  switch(func_num_args()) {
    case 0: return $db; break;
    case 1: return isset($db[$key]) ? $db[$key] : null; break;
    case 2:
      $redis->hset($obj, $key, $value);
      break;
  }
}


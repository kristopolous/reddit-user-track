<?php
require __DIR__ . '/vendor/autoload.php';

include('lib.php');
include('db.php');

$redis = new Redis();
$redis->connect('127.0.0.1', 6379);
$path = $_GET['path'];
$sub = $redis->hget('subs', $path);
if(!empty($sub)) {
    $redis->hIncrBy('subblock', $sub, 1);
    error_log(" score $sub");
} else {
    error_log("NO RECORD FOR $path");
}

$dir = dirname($_SERVER['SCRIPT_FILENAME']);
unlink($dir . '/' . parse_url($path, PHP_URL_PATH));
echo($dir . '/' . parse_url($path, PHP_URL_PATH));

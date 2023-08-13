<?php

$path = $_GET['path'];
$dir = dirname($_SERVER['SCRIPT_FILENAME']);
unlink($dir . '/' . parse_url($path, PHP_URL_PATH));

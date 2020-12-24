<?php
include('lib.php');
$url = $_GET['url'];
$path = pathinfo($url);
$flatten_url = preg_replace('/\//','_', $url);
$isMovie = is_video($url);
if ($isMovie) {
  $flatten_url = preg_replace("/.{$isMovie}/",'.jpg', $flatten_url);
}

$url = escapeshellarg($url);
if (!file_exists("tn/$flatten_url")) {
  $tn = escapeshellarg("tn/$flatten_url");
  if ($isMovie) {
    shell_exec("ffmpeg -loglevel quiet -ss 3 -i $url -vframes 1 -q:v 6 $tn");
  } else {
    shell_exec("convert $url -resize 300x $tn");
  }
}
header("Location: tn/$flatten_url");

<?php
$url = $_GET['url'];
$path = pathinfo($url);
$flatten_url = preg_replace('/\//','_', $url);
$isMovie = 0;
if ($path['extension'] == 'mp4') {
  $isMovie = 1;
  $flatten_url = preg_replace('/.mp4/','.jpg', $flatten_url);
}

$url = escapeshellarg($url);
if (!file_exists("tn/$flatten_url")) {
  $tn = escapeshellarg("tn/$flatten_url");
  if ($isMovie) {
    shell_exec("ffmpeg -loglevel quiet -ss 3 -i $url -vframes 1 -q:v 6 $tn");
  } else {
    shell_exec("convert $url -resize 200x $tn");
  }
}
header("Location: tn/$flatten_url");

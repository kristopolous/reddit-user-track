<?php
$url = $_GET['url'];
$flatten_url = preg_replace('/\//','_', $url);
if (!file_exists("tn/$flatten_url")) {
  shell_exec("convert $url -resize 200x tn/$flatten_url");
}
header("Location: tn/$flatten_url");

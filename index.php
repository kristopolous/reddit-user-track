<!doctype html5>
<link rel=stylesheet href=style.css />
<script src=remember.js></script>
<?php
$now = time();
foreach(glob("data/*/*.*") as $f) {
  if (basename($f) == 'urllist.txt') {
    continue;
  }
  
  $when = filemtime($f);
  if($now - $when < 86400 / 2) {
    $what = pathinfo($f);
    if($what['extension'] == 'mp4') {
?>
            <video class=video autoplay loop muted="" nocontrols>
            <source src=<?=$f?>>
            </video>
<?
    } else {
      echo "<img title='$f' data-src='$f'>";
    }
  }
}


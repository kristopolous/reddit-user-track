<?php
$now = time();
foreach(glob("data/*/*.*") as $f) {
  if (basename($f) == 'urllist.txt') {
    continue;
  }
  
  $when = filemtime($f);
  if($now - $when < 86400 / 2) {
    echo "<object data=$f></object>";
  }
}


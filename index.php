<!doctype html5>
<link rel=stylesheet href=style.css />
<script src=remember.js></script>
<?php

$now = time();
foreach(glob("data/*") as $user) {
  $is_first = true;
  foreach(glob("$user/*.*") as $f) {
    if (basename($f) == 'urllist.txt') {
      continue;
    }
    
    $when = filemtime($f);
    if($now - $when < 86400 / 2) {
      if($is_first) {
        $user_short = basename($user);
        echo "<div data-user='$user_short' class='cont wrap'>";
        echo "<span class=user></span>";
        echo "<div class=inner>";
        $is_first = false;
      }
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
  if(!$is_first) { 
    echo "</div>";
    echo "</div>";
  }
}

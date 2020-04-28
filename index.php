<!doctype html5>
<link rel=stylesheet href=style.css />
<script src=remember.js></script>
<?php

$now = time();
$res = [];
foreach(glob("data/*") as $user) {
  $is_first = true;
  $user_short = basename($user);
  $row = [];
  $count = 0;
  foreach(glob("$user/*.*") as $f) {
    $fname =basename($f);
    if ($fname == 'urllist.txt') {
      continue;
    }
    $row[] = $fname;
    
    $when = filemtime($f);
    if($now - $when < 86400*60 ) {
      $count ++;
      if($count > 3) {
        continue;
      }
      if($is_first) {
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
        echo "<img title='$fname' data-src='$f'>";
      }
    }
  }
  $res[$user_short] = $row;
  if(!$is_first) { 
    echo "</div>";
    echo "</div>";
  }
}
?>
<script>
  var all = <?=json_encode($res);?>
</script>

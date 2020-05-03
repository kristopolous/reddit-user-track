<!doctype html5>
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<link rel=stylesheet href=style.css /><script src=remember.js></script><div id=links>
<?php
$last = $_GET['last'] ?: 4;


foreach([2,4,8,16,36,72,24*7,24*7*3,24*7*5] as $t) {
  if ($t > 48) {
    if ($t > 24 * 14) {
      $unit = $t / (24 * 7) . " week";
    } else {
      $unit = $t / 24 . " day";
    }
  } else {
    $unit = "$t hour";
  }
  
  $klass = ($last == $t) ? 'class=active' : '';
  echo "<a $klass href='?last=$t'>$unit</a>";
}
$klass = '';
if($last == 'all') { 
  $klass = 'class=active';
  $last = 25 * 365 * 20;
}
echo "<a $klass href='?last=all'>all</a>";
echo "</div>";

$now = time();
$res = [];

foreach(glob("data/*") as $user) {
  $is_first = true;
  $user_short = basename($user);
  $row = [];
  $count = 0;
  $list = glob("$user/*.*");
  usort($list, create_function('$a,$b', 'return filemtime($b) - filemtime($a);'));
  foreach($list as $f) {

    $fname =basename($f);
    if ($fname == 'urllist.txt') {
      continue;
    }
    $row[] = $fname;
    
    $when = filemtime($f);
    if($now - $when < 3600*$last ) {
      $count ++;
      if($count > 2) {
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
        echo "<video class=video autoplay loop muted='' nocontrols><source src='$f'></video>";
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

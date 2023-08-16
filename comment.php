<?php
$user=$_GET['u'];
$content = @json_decode(file_get_contents("data/$user/commentmap.txt"));
$all = [];
echo "<title>$user</title>";
foreach($content as $k=>$v) {
  $all[] = $v;
}
sort($all);
foreach(array_unique($all) as $v) {
  echo "$v<br/>";
}
echo '<hr/>';
$all =[];
foreach(@file("data/$user/titlelist.txt") as $line) {
  $all[] = $line;
}

sort($all);
foreach(array_unique($all) as $v) {
  echo "$v<br/>";
}

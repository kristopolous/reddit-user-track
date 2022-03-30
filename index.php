<!doctype html5><meta name="viewport" content="width=device-width, initial-scale=1.0" /><link rel=stylesheet href=style.css?3 /><script src=remember.js?2></script><div id=links>
<?php

include('lib.php');
include('db.php');
$db = db();

$use_fail = isset($_GET['fail']);
$newest = $_GET['newest'] ?? 0;
$last = $_GET['last'] ?? ($newest ? 24*60*365*10 : '24');
$format = $_GET['format'] ?? '*';
$max = $_GET['max'] ?? PHP_INT_MAX;
$min = $_GET['min'] ?? 0;
$page = $_GET['page'] ?? 0;
$qstr = $_GET['q'] ?? null;
$fm = $_GET['fm'] ?? null;
$fu = $_GET['fu'] ?? 1.0;
$userList = $_GET['users'] ?? $_GET['user'] ?? $_GET['userlist'] ?? null;
$matchMap = [];

if ($format === '*') {
  $perPage = 30;
} else {
  $perPage = 5;
}

$start = $page * $perPage;
$end = ($page + 1) * $perPage;

function dolink($kv) {
  $copy = $_GET;
  foreach($kv as $k => $v) {
    if($v == false) {
      unset($copy[$k]);
    } else {
      $copy[$k] = $v;
    }
  }
  return "?" . http_build_query($copy);
}

if(!empty($userList)) {
  $last = 'all';
}

$prev = false;
foreach([2,8,24,48,96,24*7,24*7*3,24*7*8,24*7*24] as $t) {
  if ($t > 48) {
    if ($t > 24 * 14) {
      $unit = $t / (24 * 7) . " week";
    } else {
      $unit = $t / 24 . " days";
    }
  } else {
    $unit = "$t hour";
  }
  
  $klass = ($last == $t) ? 'class=active ' : '';
  $link = dolink(['last' => $t, 'newest' => $prev]);

  echo "<a ${klass}href='$link'>$unit</a>";
  $prev = $t;
}
$klass = '';
if($last == 'all') { 
  $klass = 'class=active ';
  if(empty($_GET['last'])) { 
    $last = 24 * 365 * 20;
  }
}
echo "<a ${klass}href='" . dolink(['last' => 'all']) . "'>all</a>";
?>
<form>
<input name=last type=hidden value=<?= $last ?>>
<input name=page type=hidden value=<?= $page ?>>
<input name=q placeholder=query value="<?= $qstr ?>">
<button>go</button>
</form>
</div>
<div id=content>
<?php

$now = time();
$res = [];
$filter = false;

if($use_fail) {
  $filter = array_keys(json_decode(file_get_contents('fail.json'), true));
}

if($fm) {
  $fm = floatval($fm);
  $map = json_decode(file_get_contents('facemaster.json'), true);
  $oldFilter = $filter;
  $filter = [];

  foreach($map as $k => $v) {
    if($v > $fm && $v < $fu) {
      if(count($oldFilter) == 0 || in_array($k, $oldFilter)) {
        $filter[] = $k;
      }
    }
  }
}

if(isset($userList)) {
  $toShow = explode(',',$userList);
} else {
  $toShow = glob("data/*");
  $nameList = array_map(function($r) { return substr($r, 5); }, $toShow);
  foreach($nameList as $k) {
    if(!array_key_exists($k, $db)) {
      $db[$k] = 0;
    }
    // $db[$k] = 0;
  }
  arsort($db);
  $toShow = array_keys($db);
}

if ($qstr) {
  $newToShow = [];
  $parts = explode(',', $qstr);
  $regParts = [];
  foreach($parts as $sub) {
    $regParts[] = '/.*' . $sub . '.*/i';
  }
  foreach($toShow as $user) {
    $match = true;
    foreach($regParts as $sub) {
      $match &= preg_match($sub, $user);
    }
    if(!$match) {
      if (!file_exists("data/$user/titlelist.txt")) {
        continue;
      }
      $doc = file_get_contents("data/$user/titlelist.txt");
      $match = !!strlen($doc);
      foreach($regParts as $sub) {
        $match &= preg_match_all($sub, $doc, $matches);
        if(!$match) { 
          break;
        }
        if(!array_key_exists($user, $matchMap)) {
          $matchMap[$user] = [];
        }
        foreach(array_slice($matches[0], 0, 3) as $line) {

          $matchMap[$user][] = $line;
        }
      }
    }
    if($match) {
      $newToShow[] = $user;
    }
  }
  $toShow = $newToShow;
}


$ix = 0;
foreach($toShow as $user_short) {
  $is_first = true;
  $user = "data/$user_short";
  if($filter !== false && !in_array($user_short, $filter)) {
    continue;
  }

  $row = [];
  $count = 0;
  $list = glob("$user/*.$format");
  usort($list, create_function('$a,$b', 'return filemtime($b) - filemtime($a);'));
  if ($min > count($list) || count($list) > $max ) {
    continue;
  }
  if($ix > $end) {
    break;
  }
  foreach($list as $f) {

    $fname = basename($f);
    $parts = pathinfo($fname);

    if($parts['extension'] == 'txt' || $parts['extension'] == 'json') {
      continue;
    }

    $row[] = $fname;
    
    $when = filemtime($f);
    if($newest && $now - $when < 3600 * $newest) {
      break;
    }
    if($last == 'all' || !$is_first || ($now - $when < 3600 * $last  && $now - $when > 3600 * $newest)) { // || $filter) {
      if($is_first) {
        $ix ++;
        // paging
        if($ix <= $start || $ix > $end) {
          // don't clear the is_first and we won't add it
          break;
        }
      }
      $count ++;
      if($count > 3 && $format == '*') { // || !$when)) {
        continue;
      }
      $orig = $f;
      $f = preg_replace("/%2F/", "/", urlencode($f));
      $f = preg_replace("/\&/", "%26", $f);
      if($is_first) {
        echo "\n<div data-last=" . floor(($now - $when) / 3600) . " data-user='$user_short' class='cont wrap'>";
        echo "<span class=user></span>";
        echo "<div class=inner>" ;
        if(array_key_exists($user_short, $matchMap)) {
          echo "<div class=matches><p>";
          echo implode('</p><p>', $matchMap[$user_short]);
          echo "</p></div>";
        }
        $is_first = false;
      }
      $dt = date("F d Y H:i:s", filemtime($orig));
      $dtm = round((time() - filemtime($orig))/3600);
      $dt = floor($dtm / 24) . 'd ' . $dtm % 24 . "h / $dt ";
      if(is_video($orig)) {
        echo "<video title='$dt' poster=\"tnail.php?url=$f\" class=video preload=none loop muted='' controls><source src='$f'></video>";
      } else {
        echo "\n <img title='$dt' src='tnail.php?url=$f'>";
      }
    }
  }
  if(!$is_first) { 
    $res[$user_short] = $row;
    echo "</div>";
    echo "</div>";
  }
}
echo "</div><div id=paging>";
if($page > 0) {
  echo "<a href=" . dolink(['page' => $page - 1]) . ">prev</a>";
}
if($ix > $start + $perPage) {
  echo "<a href=" . dolink(['page' => $page + 1]) . ">next</a>";
}
?></div><script>Object.assign(self,<?= json_encode([ 'all' => $res, 'db' => $db]) ?>);</script>

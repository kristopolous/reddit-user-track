<?php

function is_video($path) {
   $parts = explode('?', $path);
   $what = pathinfo($parts[0]);
   if (in_array($what['extension'], ['mp4', 'flv', 'gifv', 'gif', 'webm'])) {
     return $what['extension'];
   }
 }
   

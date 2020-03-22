#!/bin/sh
{
  cat << ENDL
<style>
body { font-size:0;margin: 0; padding: 0; background: black; }
img { width: 25% }
</style>
ENDL
  find . -name \*.jpg -or -name \*.gif -or -name \*.png | awk ' { print "<img src="$0">" } ' 
} > index.html

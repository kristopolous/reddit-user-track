#!/bin/bash
{
  cat << ENDL
<style>
a { text-decoration: none; color: #aac }
a:hover { color: #99f}
body { font-size:0;margin: 0; padding: 0; background: black; }
img { width: 33.3% }
div.wrap { width: 95% }
div.inner {margin-bottom: 2rem;max-height:60rem;overflow-y:auto;border-bottom:3px solid #777 }
span { text-indent: .5rem; font-family:sans;font-size: 20px; color: #aaa;background:#222;padding:0.5rem; display: block }
.show img { display: none }
div.inner.show { background: #333; margin-bottom: 0; }
</style>
<script src=remember.js></script>
ENDL
lastdir=''
if [[ -n "$1" ]];then 
  list=$(find . \( -name \*.jpg -or -name \*.gif -or -name \*.png \) -and -ctime -$1 ); 
else 
  list=$(find . -name \*.jpg -or -name \*.gif -or -name \*.png)
fi

for i in $list; do
  dir=$(dirname $i)
  if [[ "$dir" != "$lastdir" ]]; then
    [[ -n "$lastdir" ]] && echo "</div></div>"
    user=$(basename $dir)
    echo "<div class=wrap>"
    echo "<span><a href=https://old.reddit.com/u/$user>$user</a></span>"
    echo "<div class=inner onclick=\"this.classList.toggle('show')\">"
  fi
  echo "<img src="$i">"
  lastdir=$dir
done

echo "</div>"
} > index.html

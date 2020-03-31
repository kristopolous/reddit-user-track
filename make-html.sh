#!/bin/bash
{
  cat << ENDL
<style>
a { text-decoration: none; color: #aac }
a:hover { color: #99f}
body { font-size:0;margin: 0; padding: 0; background: black; }
img { width: 33.3% }
div.wrap { width: 97% }
div.inner {max-height:60rem;overflow-y:auto;border-bottom:3px solid #777 }
span { text-indent: .5rem; font-family:sans;font-size: 20px; color: #aaa;background:#222;padding:0.5rem; display: block }
.show img { display: none }
div.inner.show { background: #333; margin-bottom: 0; }
</style>
<script src=remember.js></script>
ENDL
lastdir=''
path="."
args=""
if [[ -e "$1" ]]; then 
  path="$1" 
elif [[ -n "$1" ]]; then 
  args=" -and -ctime -$1"
fi
list=$(find $path \( -name \*.jpg -or -name \*.gif -or -name \*.png \) $args )

for i in $list; do
  dir=$(dirname $i)
  if [[ "$dir" != "$lastdir" ]]; then
    [[ -n "$lastdir" ]] && echo "</div></div>"
    user=$(basename $dir)
    echo "<div class=wrap>"
    echo "<span><a href=https://old.reddit.com/u/$user>$user</a></span>"
    echo "<div class=inner onclick=\"this.classList.toggle('show')\">"
  fi
  echo "<img title="$i" src="$i">"
  lastdir=$dir
done

echo "</div>"
} > index.html

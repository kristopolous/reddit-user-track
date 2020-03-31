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
path="."
args=""
if [[ -e "$1" ]]; then 
  path="$1" 
elif [[ -n "$1" ]]; then 
  args="-and -ctime -$1"
fi
list=$(find $path -mindepth 1 -type d -and -not -path "*/.git*" | sort )

for dir in $list; do
  sublist=$( find $dir \( -name \*.jpg -or -name \*.gif -or -name \*.png \) $args )
  if [ -n "$sublist" ]; then
    echo "<div class=wrap>"
      user=$(basename $dir)
      echo "<span><a href=https://old.reddit.com/u/$user>$user</a></span>"
      echo "<div class=inner onclick=\"this.classList.toggle('show')\">"
        for i in $(identify -format "%[fx:w/h] %f\n" $sublist | sort -n | awk ' { print $2 } ' | uniq ); do
          echo "<img title="$i" src="$dir/$i">"
        done
      echo "</div>"
    echo "</div>"
  fi
done

} > index.html

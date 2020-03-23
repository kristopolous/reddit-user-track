#!/bin/bash
{
  cat << ENDL
<style>
body { font-size:0;margin: 0; padding: 0; background: black; }
img { width: 33.3% }
div.wrap { width: 95% }
div.inner {margin-bottom: 2rem;max-height:60rem;overflow-y:auto;border-bottom:3px solid #777 }
span { text-indent: .5rem; font-family:sans;font-size: 20px; color: #aaa;background:#222;padding:0.5rem; display: block }
.show img { display: none }
.show { background: #333; margin-bottom: 0; }
</style>
<script src=remember.js></script>
ENDL
lastdir=''
for i in $(find . -name \*.jpg -or -name \*.gif -or -name \*.png); do 
  dir=$(dirname $i)
  if [[ "$dir" != "$lastdir" ]]; then
    [[ -n "$lastdir" ]] && echo "</div></div>"
    echo "<div class=wrap>"
    echo "<span>$(basename $dir)</span>"
    echo "<div class=inner onclick=\"this.classList.toggle('show')\">"
  fi
  echo "<img src="$i">"
  lastdir=$dir
done

echo "</div>"
} > index.html

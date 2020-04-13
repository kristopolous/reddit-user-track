#!/usr/bin/zsh
my_path="."
args="-mindepth 1"
if [[ -d "data/$1" ]]; then 
  echo "using $1"
  my_path="$1" 
  args=
elif [[ -n "$1" ]]; then 
  args="$args -and -ctime -$1"
fi
list=$(find data/$my_path -type d -and -not -path "*/.git*" | sort )
{
  cat << ENDL
<style>
a { text-decoration: none; color: #aac }
a:hover { color: #99f}
body { font-size:0;margin: 0; padding: 0; background: black; }
video,img { width: 33.3% }
div.wrap { width: 97% }
div.inner {max-height:60rem;overflow-y:auto;border-bottom:3px solid #777 }
span { text-indent: .5rem; font-family:sans;font-size: 20px; color: #aaa;background:#222;padding:0.5rem; display: block }
.show img { display: none }
div.inner.show { background: #333; margin-bottom: 0; }
</style>
<script src=remember.js></script>
ENDL

for dir in $list; do
  if [ -n "$args" ]; then
    sublist=$( find $dir \( -name \*.jpg -or -name \*.mp4 -or -name \*.gif -or -name \*.png \) $args )
  else
    sublist=($dir/**/*(jpg|mp4|gif|png|jpeg)(om))
  fi

  if [ -n "$sublist" ]; then
    echo "<div class=wrap>"
      user=$(basename $dir)
      echo "<span><a href=https://old.reddit.com/u/$user>$user</a></span>"
      echo "<div class=inner onclick=\"this.classList.toggle('show')\">"
        for i in $sublist; do
          #(identify -format "%[fx:w/h] %f\n" $sublist | sort -n | awk ' { print $2 } ' | uniq ); do
          ext="${i##*.}"
          if [[ $ext == 'mp4' ]]; then
            cat << ENDL
              <video class=video autoplay loop muted="" nocontrols>
                <source src="$i">
              </video>
ENDL
          else
            echo "<img title="$i" src="$i">"
          fi
        done
      echo "</div>"
    echo "</div>"
  fi
done

} > index.html

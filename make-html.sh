#!/usr/bin/zsh
my_path="data/"
arg_first=
args=
all=

if [[ -n "$1" ]]; then
  if [[ -d "data/$1" ]]; then 
    my_path=
    all=1
    while [[ -d "data/$1" ]]; do
      my_path="$my_path data/$1" 
      echo "using $1"
      shift
      [[ -z "$1" ]] && break
      all=
    done
  elif [[ -n "$1" ]]; then 
    arg_first="-mindepth 1"
    args=" -ctime -$1"
    if [[ -n "$2" ]]; then
      if [[ "$2" == "all" ]]; then 
        all=1
        arg_first="-maxdepth 0" 
      else
        args="$args ! -ctime -$2"
      fi
    fi
  fi
else
  arg_first="-mindepth 1"
fi

list=($(find ${=my_path} ${=arg_first} -type d -and -not -path "*/.git*" -and -not -path "*__pycache__*" | sort ))
{
  cat << ENDL
<style>
a { text-decoration: none; color: #aac }
a:hover { color: #99f }
body { font-size:0;margin: 0; padding: 0; background: black; }
video,img { width: 33.3%; visibility: hidden; }
div.wrap { width: 97% }
div.inner {max-height:60rem;overflow-y:auto;border-bottom:3px solid #777 }
span { text-indent: .5rem; font-family:sans;font-size: 20px; color: #aaa;background:#222;padding:0.5rem; display: block }
.show img, .show video {visibility: visible }
</style>
<script src=remember.js></script>
ENDL

for dir in $list; do
  if [[ -z "$single" ]]; then
    sublist=($( /usr/bin/find $dir ${=args} | grep -E "(jpe?g|png|gif|mp4)" ))
  else
    sublist=($dir/**/*(jpg|mp4|gif|png|jpeg)(om))
  fi

  if [ -n "$sublist" ]; then
    echo "<div class=wrap$all>"
      user=$(basename $dir)
      echo "<span><a href=https://old.reddit.com/u/$user>$user</a></span>"
      [[ -z $all ]] && echo "<div class=inner>"
        for i in $sublist; do
          #(identify -format "%[fx:w/h] %f\n" $sublist | sort -n | awk ' { print $2 } ' | uniq ); do
          ext="${i##*.}"
          if [[ $ext == 'mp4' ]]; then
            cat << ENDL
              <video class=video autoplay loop muted="" nocontrols>
                <source data-src="$i">
              </video>
ENDL
          else
            echo "<img title="$i" data-src="$i">"
          fi
        done
      [[ -z $all ]] && echo "</div>"
    echo "</div>"
  fi
done

} > index.html

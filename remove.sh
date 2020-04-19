#!/bin/bash
if [[ -e data/$1 ]]; then 
  echo "Removed: " $(ls data/$1 | wc -l)
  rm -r data/$1
  sed -i '/'$1'/d' userlist.txt
else 
  echo $1 >> banlist.txt
fi
#./make-html.sh

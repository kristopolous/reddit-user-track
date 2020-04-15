#!/bin/bash
if [[ -e data/$1 ]]; then 
  rm -r data/$1
  sed -i '/'$1'/d' userlist.txt
else 
  echo $1 >> banlist.txt
fi
./blockem.py 
#./make-html.sh

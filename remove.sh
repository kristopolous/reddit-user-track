#!/bin/bash
while [[ -n "$1" ]]; do
  if [[ -e data/$1 ]]; then 
    echo "Removed: "$(ls data/$1 | wc -l)
    mv data/$1 /tmp/
    [[ -e data/$1 ]] && rm -r data/$1
    sed -i '/'$1'/d' userlist.txt
  fi
  echo $1 del $(date) >> .log.txt
  echo $1 >> banlist.txt
  shift
done

sort banlist.txt | uniq > /tmp/blist
mv /tmp/blist banlist.txt
./blockem.py

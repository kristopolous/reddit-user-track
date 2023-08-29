#!/bin/bash

today=$(date +%m%d%H)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR
. secrets.sh
truncate --size 0 last_output
n=0
names=''
timeout=2m
for i in $(ls data/); do
  (( n++ ))
  who=$(basename $i)
  if (( n % 10 == 0 )); then
    ( timeout $timeout ./pull.py $names >> last_output 2>&1 ) &
    sleep 10
    names=''
  else
    names="$names $i"
  fi
done

if [[ -n "$names" ]]; then
  timeout $timeout ./pull.py $names >> last_output 2>&1
fi

./facer.py

for i in ${subs[@]}; do
  ./sub.py $i
done

#flock -n /tmp/$today ./pull.py || exit 0
echo $(whoami) $(date) $today $DIR >> last_run
#./redgif-pull.sh && touch last_run.txt

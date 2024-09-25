#!/bin/bash

today=$(date +%m%d%H)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR
. secrets.sh
truncate --size 0 last_output
n=0
names=''
timeout=5m
source env/bin/activate
find data -size 0c -name \*.jpg -exec rm {} \;

for i in $(ls data/ | shuf); do
  (( n++ ))
  who=$(basename -- "$i")
  if (( n % 4 == 0 )); then
    ( timeout $timeout ./pull.py $names >> last_output 2>&1 ) &
    sleep 15
    names=''
  else
    names="$names $i"
  fi
done

if [[ -n "$names" ]]; then
  timeout $timeout ./pull.py $names >> last_output 2>&1
fi

./facer.py &

for i in ${subs[@]}; do
  ./sub.py $i
done

{
cat rating.json | jq -n -r <<SCRIPT
  to_entries 
  | map(select((.value | tonumber)< -5)) 
  | from_entries 
  | keys[]
SCRIPT
} | grep -Ev '^null$' | while read i
  do ./remove.sh $i
done


#flock -n /tmp/$today ./pull.py || exit 0
echo $(whoami) $(date) $today $DIR >> last_run
#./redgif-pull.sh && touch last_run.txt

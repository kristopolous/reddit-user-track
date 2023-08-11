#!/bin/bash

today=$(date +%m%d%H)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR
. secrets.sh
timeout 50m ./pull.py > $HOME/last_output 2>&1
./facer.py

for i in ${subs[@]}; do
  ./sub.py $i
done

#flock -n /tmp/$today ./pull.py || exit 0
echo $(whoami) $(date) $today $DIR >> $HOME/last_run
#./redgif-pull.sh && touch last_run.txt

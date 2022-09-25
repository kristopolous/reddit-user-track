#!/bin/bash

today=$(date +%m%d%H)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR
flock -n /tmp/$today ./pull.py  || exit 0
#./redgif-pull.sh && touch last_run.txt

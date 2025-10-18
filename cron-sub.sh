#!/bin/bash

today=$(date +%m%d%H)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR
. secrets.sh
truncate --size 0 last_output
n=0
names=''
source env/bin/activate

for i in ${subs[@]}; do
./sub.py $i
done

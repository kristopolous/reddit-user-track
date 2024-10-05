#!/bin/bash
while [[ -n "$1" ]]; do
  [[ -z "$1" ]] && exit
  [[ -e banlist.txt ]] && sed -i '/'$1'/d' banlist.txt
  echo $1 >> userlist.txt
  source env/bin/activate
  python3 ./pull.py $1
  echo $1 add $(date) >> .log.txt
  shift
done
#./blockem.py

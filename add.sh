#!/bin/bash
while [[ -n "$1" ]]; do
  [[ -z "$1" ]] && exit
  echo $1 >> userlist.txt
  ./pull.py $1
  shift
done
./blockem.py

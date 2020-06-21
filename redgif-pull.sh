#!/bin/bash
start=$PWD
for i in data/*; do
  cd $i
  touch donelist.txt
  for i in $(cat urllist.txt donelist.txt | grep redgifs | sort | uniq -u); do
    youtube-dl "$i"
    echo "$i" >> donelist.txt
  done
  cd $start
done

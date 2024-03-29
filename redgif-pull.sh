#!/bin/bash
start=$PWD
echo -e "\n" > /tmp/newline
for i in data/*; do
  if [[ -e $i ]]; then
    cd $i
    if [ -e "urllist.txt" ]; then
      touch donelist.txt

      for f in donelist urllist; do
        grep -Ev '\w\whttps:' $f.txt > /tmp/list
        mv /tmp/list $f.txt
      done

      for j in $(cat urllist.txt /tmp/newline donelist.txt | grep redgifs | sort | uniq -u); do
        yt-dlp -R 120 -r 70k "$j" && echo "$j" >> donelist.txt
      done
    fi
    cd $start
  fi
done

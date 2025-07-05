#!/bin/bash

gif2mp4() {
  total=$(ls data/*/*.gif | wc -l)
  count=0
  for i in data/*/*.gif; do
    new="${i/gif/mp4}"
    ffmpeg -y -loglevel -3 -i "${i}" -crf 27 "${new}"
    [[ -s "${i/gif/mp4}" ]] && rm -- "${i}"
    echo $count $total "$i -> $new"
    (( count++ ))
  done
}

mobilecleanup() {
  for i in data/*/*.mp4; do
    mobile="${i/.mp4/-mobile.mp4}"
    incr="${mobile/(1)/(2)/}"
    [[ -s "$incr" ]] && echo rm "$incr"
  done
}

gif2mp4
mobilecleanup

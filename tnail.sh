#!/bin/bash
[[ -e tn ]] || mkdir tn
cd data
sz=100
for d in *; do
  ls $d/*.[jp]* | head -10 | while read i; do
    tn="${d}_$(basename $i)"
    echo $tn
    [[ -e ../tn/$tn ]] || convert "$i" -resize "${sz}x${sz}^" -gravity Center -extent ${sz}x${sz} "../tn/$tn"
    #identify "../tn/$tn"

  done
done

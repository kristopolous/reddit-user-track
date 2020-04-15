#!/bin/bash
[[ -z "$1" ]] && exit
echo $1 >> userlist.txt
./pull.py $1

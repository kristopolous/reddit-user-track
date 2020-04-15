#!/bin/bash
[[ -z "$1" ]] && exit
echo $1 >> userlist.txt
./blockem.py
./pull.py $1

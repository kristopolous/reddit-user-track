#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR
./pull.py 
./redgif-pull.sh && touch last_run.txt

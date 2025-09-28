#!/bin/bash
cat data/*/sub*list.txt | sed -E 's/\]/\n/g'  | awk -F '"' ' { print $4"\t\t\t"$2 } ' | sort | grep $(date +%Y%m) | uniq -c -w 10 | sort -n  > candidate-list.txt
./get-my-subs.py > my-sub-list.txt
grep -vf my-sub-list.txt candidate-list.txt


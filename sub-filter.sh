#!/bin/bash
if [[ ! -e candidate-list.txt ]]; then 
    cat data/*/sub*list.txt | \
        sed -E 's/\]/\n/g'  | \
        awk -F '"' ' { printf " %-30s %s\n", $4, $2 } ' | \
        sort | grep $(date +%Y) | \
        uniq -c -w 10 | \
        sort -n  > candidate-list.txt;
fi

[[ -e my-sub-list.txt ]] || { ./get-my-subs.py > my-sub-list.txt; }
grep -vf my-sub-list.txt candidate-list.txt


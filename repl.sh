#!/bin/bash
while read -e -p ">> " action; do
  user=${action:1}
  action=${action:0:1}
  [[ $action == '+' ]] && ./add.sh $user &
  [[ $action == '-' ]] && ./remove.sh $user 
  echo $(( 1000 * $(cat userlist.txt | wc -l) / $(cat blocked.txt | wc -l) ))% 
done

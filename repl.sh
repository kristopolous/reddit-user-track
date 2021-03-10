#!/bin/bash
while read -e -p ">> " action; do
  user=${action:1}
  action=${action:0:1}
  if [[ -z "$user" ]]; then  
    user=$(xwininfo -root -tree | grep Google\ Chrome | awk '{ print $4 } '
    )
    echo "${action}${user}"
  fi
  [[ $action == '+' ]] && ./add.sh $user &
  [[ $action == '-' ]] && ./remove.sh $user 
  echo "Following: $(cat userlist.txt | wc -l)"
  echo "  Blocked: $(cat blocked.txt | wc -l)"
  echo $(( 1000 * $(cat userlist.txt | wc -l) / $(cat blocked.txt | wc -l) ))% 
done

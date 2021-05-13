#!/bin/bash
while read -e -p ">> " action; do
  user=${action:1}
  action=${action:0:1}
  if [[ -z "$user" ]]; then  
    user=$(xwininfo -root -tree | grep Google\ Chrome | grep -E "(submitted|overview)" | awk '{ print $4 } ' )
    if [[ -z "$user" ]]; then
      user=$(xwininfo -root -tree | grep Google\ Chrome | grep -Po "(?<=\(u\/)([^\)]*)" )
    fi
    echo "${action}${user}"
  fi
  [[ $action == '+' ]] && ./add.sh $user &
  [[ $action == '-' ]] && ./remove.sh $user 
  echo "Following: $(cat userlist.txt | wc -l)"
  echo "  Blocked: $(cat blocked.txt | wc -l)"
  echo $(( 100000 * $(cat userlist.txt | wc -l) / $(cat blocked.txt | wc -l) ))% 
done

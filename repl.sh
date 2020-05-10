#!/bin/bash
while [ 0 ] ; do
  read -p ">> " action
  user=${action:1}
  action=${action:0:1}
  [[ $action == '+' ]] && ./add.sh $user &
  [[ $action == '-' ]] && ./remove.sh $user &
done

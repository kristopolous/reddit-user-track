#!/bin/sh
rm -r $1
sed -i '/'$1'/d' userlist.txt
./make-html.sh

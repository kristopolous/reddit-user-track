#!/bin/bash

[[ -z "$1" ]] && exit
cd data
ls "$1"
read
rm -r "$1"

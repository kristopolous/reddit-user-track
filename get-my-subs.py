#!/usr/bin/env python3
import praw
import os
import mysecrets
import json
import sys
import pdb
reddit = praw.Reddit(
    client_id=mysecrets.reddit['pull']['id'], 
    client_secret=mysecrets.reddit['pull']['secret'], 
    password=mysecrets.reddit['pull']['password'], user_agent='test', 
    username=mysecrets.reddit['pull']['username']
)

for s in reddit.user.subreddits():
    print(s)

sys.exit(0)

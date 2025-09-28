#!/usr/bin/env python3
import praw
import os
import mysecrets
import json
import sys
import pdb
reddit = praw.Reddit(
    client_id=mysecrets.reddit['block']['id'], 
    client_secret=mysecrets.reddit['block']['secret'], 
    password=mysecrets.reddit['block']['password'], user_agent='test', 
    username=mysecrets.reddit['block']['username']
)

for s in reddit.user.subreddits():
    print(s)

sys.exit(0)

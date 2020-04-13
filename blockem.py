#!/usr/bin/env python3
from glob import glob
import praw
import os
import urllib
from urllib.parse import urlparse
import secrets
import json
import sys
import inspect

reddit = praw.Reddit(
    client_id=secrets.reddit['id'], 
    client_secret=secrets.reddit['secret'], 
    password=secrets.reddit['password'], user_agent='test', 
    username=secrets.reddit['username']
)

def lf(path):
    if os.path.exists(path):
        with open(path) as fp:
            return sorted(list(set([x[1].strip('/\n ') for x in enumerate(fp)])), key=str.casefold)
    return []

print(set(lf('ignore.txt')))
all = set(lf('banlist.txt') + lf('userlist.txt')) - set(lf('ignore.txt'))

sys.exit(0)
for who in list(all):
    print(who)
    try:
        reddit.redditor(who).block()
    except:
        print("hrmm ... can't find {}".format(who))


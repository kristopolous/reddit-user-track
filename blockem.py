#!/usr/bin/env python3
import praw
import os
import secrets
import pdb
import logging

handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
for logger_name in ("praw", "prawcore"):
      logger = logging.getLogger(logger_name)
      logger.setLevel(logging.DEBUG)
      logger.addHandler(handler)

reddit = praw.Reddit(
    client_id=secrets.reddit['block']['id'], 
    client_secret=secrets.reddit['block']['secret'], 
    password=secrets.reddit['block']['password'], user_agent='test', 
    username=secrets.reddit['block']['username']
)

def lf(path):
    if os.path.exists(path):
        with open(path) as fp:
            return sorted(list(set([x[1].strip('/\n ') for x in enumerate(fp)])), key=str.casefold)
    return []

current_blocked = set(lf('banlist.txt') + lf('userlist.txt')) 
blocked = lf('blocked.txt')
all = current_blocked - set(lf('fail.txt') + blocked)

print("Total: {}".format(len(current_blocked)))

for who in all:
    print(who)
    try:
        reddit.redditor(who).block()
        blocked.append(who)
    except Exception as ex:
        print("hrmm ... can't find {} {}".format(who,ex))

with open('blocked.txt', 'w') as f:
    f.write('\n'.join(list(blocked)))

#!/usr/bin/env python3
import praw
import os
import secrets

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

blocked = lf('blocked.txt')
all = set(lf('banlist.txt') + lf('userlist.txt')) - set(lf('fail.txt') + blocked)

for who in sorted(list(all)):
    print(who)
    try:
        reddit.redditor(who).block()
        blocked.append(who)
    except:
        print("hrmm ... can't find {}".format(who))

with open('blocked.txt', 'w') as f:
    f.write('\n'.join(list(blocked)))

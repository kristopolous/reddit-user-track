#!/usr/bin/env python3
import praw
import os
import urllib
import secrets
import hashlib
import sys

reddit = praw.Reddit(client_id=secrets.client_id, client_secret=secrets.client_secret, password=secrets.password, user_agent='test', username=secrets.username)

ignore = False
with open('ignore.txt') as fp:
    ignore = set(fp.read().splitlines())

hashset = set()

with open('userlist.txt') as fp:
    for cnt, who in enumerate(fp):
        who = who.strip('/\n ')
        submissions = reddit.redditor(who).new()
        if not os.path.exists(who):
            print("Making dir: {}".format(who))
            os.mkdir(who)
        else:
            print("<< {} >>".format(who))

        for x in submissions:
            try:
                filename = os.path.basename(x.url)
            except:
                continue

            if len(filename) == 0:
                continue

            path = "{}/{}".format(who, filename)

            if path in ignore:
                print("Ignoring: {}".format(filename))
                continue

            if not os.path.exists(path):
                print(" --> {}".format(path))
                urllib.request.urlretrieve(x.url, path)
            else:
                print("Exists: {}".format(filename))

            md5 = hashlib.md5(open(path, 'rb').read()).hexdigest()

            if md5 in hashset:
                print("dupe: {}".format(filename))
                ignore.add(path)
                os.unlink(path)
            else:
                hashset.add(md5)

with open('ignore.txt', 'w') as f:
    f.write('\n'.join(list(ignore)))

#!/usr/bin/env python3
import praw
import os
import urllib
import secrets

reddit = praw.Reddit(client_id=secrets.client_id, client_secret=secrets.client_secret, password=secrets.password, user_agent='test', username=secrets.username)
with open('userlist.txt') as fp:
    for cnt, who in enumerate(fp):
        who = who.strip()
        submissions = reddit.redditor(who).new()
        if not os.path.exists(who):
            print("Making dir: {}".format(who))
            os.mkdir(who)

        for x in submissions:
            try:
                filename = os.path.basename(x.url)
                path = "{}/{}".format(who, filename)
                if not os.path.exists(path):
                    print(" --> {}".format(path))
                    urllib.request.urlretrieve(x.url, path)
                else:
                    print("Exists: {}".format(filename))
            except:
                pass

#!/usr/bin/env python3
import praw
import os
import urllib
import secrets
import hashlib
import sys

reddit = praw.Reddit(client_id=secrets.client_id, client_secret=secrets.client_secret, password=secrets.password, user_agent='test', username=secrets.username)

ignore = set()
fail = set()

if os.path.exists('ignore.txt'):
    with open('ignore.txt') as fp:
        ignore = set(fp.read().splitlines())

if os.path.exists('fail.txt'):
    with open('fail.txt') as fp:
        fail = set(fp.read().splitlines())

hashset = set()

with open('userlist.txt') as fp:
    all = list(set([x[1].strip('/\n ') for x in enumerate(fp)]))

    for who in all:
        if who in fail:
            print("Skipping {}".format(who))
            continue

        try:
            submissions = reddit.redditor(who).new()
        except:
            print("who is {}".format(who))
            continue

        if not os.path.exists(who):
            print("Making dir: {}".format(who))
            os.mkdir(who)
        else:
            print("<< {} >>".format(who))

        urllist = set()
        if os.path.exists("{}/urllist.txt".format(who)):
            with open("{}/urllist.txt".format(who)) as fp:
                urllist = set(fp.read().splitlines())

        try:
            submissions = list(submissions)
        except:
            print("Woops, no submissions {}".format(who))
            fail.add(who)
            continue

        for x in submissions:
            try:
                filename = os.path.basename(x.url)
            except:
                continue

            urllist.add(x.url)
            if len(filename) == 0:
                continue

            path = "{}/{}".format(who, filename)

            if path in ignore:
                # print("Ignoring: {}".format(filename))
                pass
                continue

            if not os.path.exists(path):
                print(" --> {}".format(path))
                try:
                    urllib.request.urlretrieve(x.url, path)
                except Exception as ex:
                    print("woops, can't get {}: {}".format(x.url, ex))
                    ignore.add(path)
                    continue
            else:
                # print("Exists: {}".format(filename))
                pass

            md5 = hashlib.md5(open(path, 'rb').read()).hexdigest()

            if md5 in hashset:
                print("dupe: {}".format(filename))
                ignore.add(path)
                os.unlink(path)
            else:
                hashset.add(md5)

        with open("{}/urllist.txt".format(who), 'w') as fp:
            fp.write('\n'.join(list(urllist)))

with open('fail.txt', 'w') as f:
    f.write('\n'.join(list(fail)))

with open('ignore.txt', 'w') as f:
    f.write('\n'.join(list(ignore)))

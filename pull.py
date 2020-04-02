#!/usr/bin/env python3
from glob import glob
import praw
import os
import urllib
import secrets
import json
import sys
import pdb
import hashlib
import inspect
from PIL import Image
import imagehash

reddit = praw.Reddit(client_id=secrets.client_id, client_secret=secrets.client_secret, password=secrets.password, user_agent='test', username=secrets.username)

def lf(path, kind = 'set'):
    if os.path.exists(path):
        with open(path) as fp:
            if kind == 'json':
                try:
                    return json.load(fp)
                except:
                    return {}

            return set(fp.read().splitlines())

ignore = lf('ignore.txt') or set()
fail = lf('fail.txt') or set()
cksum = lf('cksum.json', 'json') or {}

def cksumcheck(filename, path):
    global cksum
    global ignore

    style= 'md5'
    ext = os.path.splitext(path)[1]
    if ext in ['.jpg','.png']:
        try:
            ihash = imagehash.average_hash(Image.open(path))
            style = 'ihash'

        except:
            style='md5'

    if style == 'md5':
        ihash = hashlib.md5(open(path, 'rb').read()).hexdigest()
        style='md5'

    #print(style,ext,ihash,path)

    ihash = str(ihash)

    if ihash in cksum and cksum.get(ihash) != filename:
        print("  dupe: {}".format(filename))
        ignore.add(path)
        os.unlink(path)
    else:
        cksum[ihash] = filename

if len(sys.argv) > 1:
    user = sys.argv[1].strip()
    if user:
       submissions = reddit.redditor(user).submissions.new()
       for s in submissions:
           print(s.url)
       sys.exit(0)

with open('userlist.txt') as fp:
    all = list(set([x[1].strip('/\n ') for x in enumerate(fp)]))

    for who in all:

        if not os.path.exists(who):
            print(" /{} (Making dir)".format(who))
            os.mkdir(who)
        else:
            print(" /{}".format(who))

        cksum_seen = list(cksum.values())
        for path in glob("{}/*[jp][np]g".format(who)):
            filename = os.path.basename(path)
            if filename not in cksum_seen:
                cksumcheck(filename, path)

        if who in fail:
            print("Skipping {}".format(who))
            continue

        urllist = set()
        if os.path.exists("{}/urllist.txt".format(who)):
            with open("{}/urllist.txt".format(who)) as fp:
                urllist = set(fp.read().splitlines())

        try:
            submissions = reddit.redditor(who).submissions.new()
        except:
            print("who is {}".format(who))
            continue

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
                #print("  Ignoring: {}".format(filename))
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

            md5check(filename, path)

        with open("{}/urllist.txt".format(who), 'w') as fp:
            fp.write('\n'.join(list(urllist)))

with open('fail.txt', 'w') as f:
    f.write('\n'.join(list(fail)))

with open('ignore.txt', 'w') as f:
    f.write('\n'.join(list(ignore)))

with open('cksum.json', 'w') as f:
    json.dump(cksum, f)

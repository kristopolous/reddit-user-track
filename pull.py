#!/usr/bin/env python3
from glob import glob
import praw
import os
import urllib
from urllib.parse import urlparse
import secrets
import json
import sys
import pdb
import hashlib
import inspect
from PIL import Image
import imagehash
from gfycat.client import GfycatClient

reddit = praw.Reddit(
    client_id=secrets.reddit['id'], 
    client_secret=secrets.reddit['secret'], 
    password=secrets.reddit['password'], user_agent='test', 
    username=secrets.reddit['username']
)

gfycat = GfycatClient(
    secrets.gfycat['id'],
    secrets.gfycat['secret']
)

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
    all = [sys.argv[1].strip()]

else: 
    with open('userlist.txt') as fp:
        all = sorted(list(set([x[1].strip('/\n ') for x in enumerate(fp)])), key=str.casefold)

for who in all:
    content = "data/{}".format(who)

    if not os.path.exists(content):
        print(" /{} (Making dir)".format(content))
        os.mkdir(content)
    else:
        print(" /{}".format(content))

    cksum_seen = list(cksum.values())
    for path in glob("{}/*[jp][np]g".format(content)):
        filename = os.path.basename(path)
        if filename not in cksum_seen:
            cksumcheck(filename, path)

    if who in fail:
        print("Skipping {}".format(who))
        continue

    urllist = set()
    if os.path.exists("{}/urllist.txt".format(content)):
        with open("{}/urllist.txt".format(content)) as fp:
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

        path = "{}/{}".format(content, filename)

        if filename in ignore:
            #print("  Ignoring: {}".format(filename))
            continue

        parts = urlparse(x.url)
        url_to_get = x.url

        if parts.netloc == 'gfycat.com':
           path += '.mp4'

        if not os.path.exists(path):
            print(" --> {}".format(path))
            if parts.netloc == 'gfycat.com':
                url_path = parts.path.strip('/')
                try:
                    obj = gfycat.query_gfy(url_path)
                    url_to_get = obj.get('gfyItem').get('mp4Url')
                    print("     \_{}".format(url_to_get))

                except:
                    print("     \_ Unable to get {}".format(x.url))
                    ignore.add(path)
                    continue

            try:
                urllib.request.urlretrieve(url_to_get, path)

            except Exception as ex:
                print("woops, can't get {}: {}".format(x.url, ex))
                ignore.add(path)
                continue
        else:
            # print("Exists: {}".format(filename))
            pass

        cksumcheck(filename, path)

    with open("{}/urllist.txt".format(content), 'w') as fp:
        fp.write('\n'.join(list(urllist)))

with open('fail.txt', 'w') as f:
    f.write('\n'.join(list(fail)))

with open('ignore.txt', 'w') as f:
    f.write('\n'.join(list(ignore)))

with open('cksum.json', 'w') as f:
    json.dump(cksum, f)

#!/usr/bin/env python3
import praw
import os
import urllib
import secrets
import json
import sys
import pdb
import hashlib
import imagehash
from glob import glob
from PIL import Image
from urllib.parse import urlparse
from gfycat.client import GfycatClient
from imgurpython import ImgurClient

reddit = praw.Reddit(
    client_id=secrets.reddit['pull']['id'], 
    client_secret=secrets.reddit['pull']['secret'], 
    password=secrets.reddit['pull']['password'], user_agent='test', 
    username=secrets.reddit['pull']['username']
)

gfycat = GfycatClient(
    secrets.gfycat['id'],
    secrets.gfycat['secret']
)

imgur = ImgurClient(
    secrets.imgur['id'],
    secrets.imgur['secret']
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

def cksumcheck(path):
    global cksum
    global ignore

    style = 'md5'
    ext = os.path.splitext(path)[1]
    filename = os.path.basename(path)
    if ext in ['.jpg','.png']:
        try:
            ihash = imagehash.average_hash(Image.open(path))
            style = 'ihash'

        except:
            style = 'md5'

    if style == 'md5':
        ihash = hashlib.md5(open(path, 'rb').read()).hexdigest()
        style='md5'

    #print(style,ext,ihash,path)

    ihash = str(ihash)

    if ihash in cksum and not ( filename in cksum[ihash] or cksum[ihash] in filename ):
        print("   == {} is {} ".format(filename, cksum.get(ihash)))
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

    cksum_seen = list(cksum.values())
    if os.path.exists(content):
        for path in glob("{}/*[jp][np]g".format(content)):
            filename = os.path.basename(path)
            if filename not in cksum_seen:
                cksumcheck(path)

    if who in fail:
        print(" -- {}".format(who))
        continue

    if not os.path.exists(content):
        print(" /{} (Making dir)".format(who))
        os.mkdir(content)
    else:
        print(" /{}".format(who))


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

    for entry in submissions:
        try:
            filename = os.path.basename(entry.url)
        except:
            continue

        if len(filename) == 0:
            continue

        path = "{}/{}".format(content, filename)

        if filename in ignore:
            #print("  Ignoring: {}".format(filename))
            continue

        parts = urlparse(entry.url)
        url_to_get = entry.url

        if parts.netloc == 'gfycat.com':
           path += '.mp4'

        if not entry.url in urllist: 
            print(" \_{}".format(path))
            if parts.netloc in ['imgur.com','i.imgur.com']:
                noext = os.path.splitext(parts.path)[0]
                pieces = noext.strip('/').split('/')
                try:
                    if pieces[0] == 'a':
                        for x in imgur.get_album_images(pieces[1]):
                            url_to_get = x.link

                    else:
                        obj = imgur.get_image(pieces[0])
                        url_to_get = obj.link

                except:
                    print("   \_ Unable to get {}".format(entry.url))
                    ignore.add(path)
                    continue

                hasext = os.path.splitext(path)
                if not hasext[1]:
                    ext = os.path.splitext(url_to_get)[1]
                    path += ext

                print("   \_{}".format(url_to_get))

            if parts.netloc == 'gfycat.com':
                url_path = parts.path.strip('/')
                try:
                    obj = gfycat.query_gfy(url_path)
                    url_to_get = obj.get('gfyItem').get('mp4Url')
                    print("   \_{}".format(url_to_get))

                except:
                    print("   \_ Unable to get {}".format(entry.url))
                    ignore.add(path)
                    continue

            try:
                urllib.request.urlretrieve(url_to_get, path)
                urllist.add(entry.url)

            except Exception as ex:
                print("woops, can't get {}: {}".format(entry.url, ex))
                ignore.add(path)
                continue
        else:
            # print("Exists: {}".format(filename))
            pass

        if not os.path.exists(path):
            attempt = glob("{}.*".format(path))
            if len(attempt) > 0:
                path = attempt[0]

        if os.path.exists(path):
            cksumcheck(path)

    with open("{}/urllist.txt".format(content), 'w') as fp:
        fp.write('\n'.join(list(urllist)))

for i in ['fail', 'ignore']:
    with open(i + '.txt', 'w') as f:
        f.write('\n'.join(list(globals().get(i))))

with open('cksum.json', 'w') as f:
    json.dump(cksum, f)

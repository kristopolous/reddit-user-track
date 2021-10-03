#!/usr/bin/env python3
import os
import urllib
import json
import sys
import hashlib
import imagehash
from PIL import Image
from urllib.parse import urlparse


def lf(path, kind = 'set'):
    if os.path.exists(path):
        with open(path) as fp:
            if kind == 'json':
                try:
                    return json.load(fp)
                except:
                    return {}

            return set(fp.read().splitlines())
cksum = lf('cksum.json', 'json') or {}

def get(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'})
    return urllib.request.urlopen(request)

def cksumcheck(path, doDelete=True, who=None):
    global cksum

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

    if ihash in cksum and not ( filename in cksum[ihash][1] or cksum[ihash][1] in filename ):
        print("   == {} is {} ".format(filename, cksum.get(ihash)))
        ignore[path] = ihash
        return False
    else:
        print(style, "unique", ihash)
        cksum[ihash] = [who, filename]

    return True

remote = get(sys.argv[1])

with open('/tmp/tocheck.jpg', 'bw') as f:
  f.write(remote.read())

cksumcheck('/tmp/tocheck.jpg')

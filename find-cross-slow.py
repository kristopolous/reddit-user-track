#!/usr/bin/env python3
import pdb
import redis
import sys
import json
from PIL import Image
import imagehash
import os
from imagehash import ImageMultiHash
from pprint import pprint
from hexhamming import hamming_distance_string
r = redis.Redis(host='localhost', port=6379, db=0,charset="utf-8", decode_responses=True)

hdict={}
pdict={}
ulist={}
ll={}

USERMAX = 200 
# This records the checksum as having a single user
for k,v in r.hgetall('cksum').items():
    v = json.loads(v)
    user = v[0]
    if 'data_' in v[1]:
        continue
    if user not in ulist:
        ulist[user] = 0

    ulist[user] += 1
    hdict[k] = user
    pdict[k] = v[1]


"""
# Now we go through the ignore list
for k,v in r.hgetall('ignore').items():
    parts = k.split('/')

    if len(parts) > 1:
        if parts[0] == 'data':
            user = parts[1]
    if v not in hdict:
        hdict[v] = set()

    # if we find the checksum again we add another user to it
    hdict[v].add(user)
"""

# Create the lookup table for a hamming distance calculation.
for hx in hdict.keys():
    stub = hx[:2]
    if stub == "na":
        print(hx)
    else:
        mylen = len(hx)
        if mylen not in ll:
            ll[mylen] = {}
        if stub not in ll[mylen]:
            ll[mylen][stub] = set()
        ll[mylen][stub].add(hx)

# Now here's the sloooow part.
ttl = len(hdict.keys())
ix=0

hcache = {}

def compare(h1, h2, d):
    global hcache

    path1="data/{}/{}".format(hdict[h1], pdict[h1])
    path2="data/{}/{}".format(hdict[h2], pdict[h2])
    key=":".join(sorted([path1,path2]))
    crh = r.hget('crh', key)

    if not os.path.exists(path1) or not os.path.exists(path2):
        return

    o = ""
    if not crh:

        ch1 = r.hget('cr', path1)
        if not ch1:
            ch1 = imagehash.crop_resistant_hash(Image.open(path1))
            r.hset('cr', path1, str(ch1))
            o += "+"
        else:
            ch1 = imagehash.hex_to_multihash(ch1)
            o += "."

        ch2 = r.hget('cr', path2)
        if not ch2:
            ch2 = imagehash.crop_resistant_hash(Image.open(path2))
            r.hset('cr', path2, str(ch2))
            o += "+"
        else:
            ch2 = imagehash.hex_to_multihash(ch2)
            o += "."

        crh = ch1 - ch2
        if o != "..":
            print("{} {} {}:{}".format(o, cix,path1,path2), file=sys.stderr)

        r.hset('crh', key, crh)

    crh = float(crh)

    if (crh < 1.2):
        print(' '.join(sorted([path1, path2])), crh, d, ','.join(sorted([hdict[h1],hdict[h2]])),flush=True)
        sys.stdout.flush()


cix=0
for len_ix in ll:
    llm = sorted(ll[mylen].keys())
    for stub_ix in llm:

        tocompare = []
        
        for bucket_stub in ll[mylen].keys():
            if hamming_distance_string(stub_ix,bucket_stub) < 2:
                tocompare.append(bucket_stub)


        for hx in ll[len_ix][stub_ix]:
            ix += 1
            if ix % 50 == 0:
                print(100 * ix / ttl, file=sys.stderr)

            for bucket_stub in tocompare:
                for what in ll[len_ix][bucket_stub]:
                    hd = hamming_distance_string(what, hx) 
                    if hd < 6:
                        if hdict[hx] != hdict[what]:
                            cix += 1
                            compare(hx,what, hd)


        del ll[mylen][stub_ix]


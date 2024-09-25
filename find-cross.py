#!/usr/bin/env python3
import redis
import sys
import json
from collections import Counter
r = redis.Redis(host='localhost', port=6379, db=0,charset="utf-8", decode_responses=True)

cutoff = int(sys.argv[1]) if len(sys.argv) > 1 else 6

hdict = {}

# This records the checksum as having a single user
for k,v in r.hgetall('cksum').items():
    v = json.loads(v)
    if k not in hdict:
        hdict[k] = []
    hdict[k].append(v[0])


# Now we go through the ignore list
for k,v in r.hgetall('ignore').items():
    parts = k.split('/')

    if len(parts) > 1:
        if parts[0] == 'data':
            user = parts[1]
    if v not in hdict:
        hdict[v] = []

    # if we find the checksum again we add another user to it
    hdict[v].append(user)

# k is the hash, l is the list of users associated with the hash
matchSet = {}
for k,l in hdict.items():
    v = set(l)
    # Now we try to find how many users posted an identical photograph
    if len(v) > 1:
        # We sort things so that the earliest name
        # will be used as the comparator key
        nameList = list(sorted(list(v)))
        lhs = nameList[0]

        if lhs not in matchSet:
            matchSet[lhs] = {}

        # We go through the rest of the matches and
        # then increment if we've seen the names match
        for who in nameList[1:]:
            if who not in matchSet[lhs]:
                matchSet[lhs][who] = 1
            else:
                matchSet[lhs][who] += 1
        
        #print(list(sorted(list(v))))

for k,ma in matchSet.items():
    ma_list = list(ma.keys())
    # Some users post a lot of other users, we do a cutoff at 6.
    if len(ma_list) < cutoff:
        #print(ma_list)
        mlist = [k] + ma_list
        for a in ma.keys():
            if a in matchSet:
                ma_list = list(matchSet[a].keys())
                if len(ma_list) < cutoff:
                    mlist += matchSet[a].keys()

        mlist = list(sorted(set(mlist)))
        for i in range(0, len(mlist)-1, 2):
            print(','.join(mlist[i:i+2]))
        #print("{} \t {}".format(len(mlist),','.join(mlist)))
        #for who,freq in ma.items():
        #print("{} {:30} {}".format(freq,k,who))
        #print(json.dumps(matchSet))


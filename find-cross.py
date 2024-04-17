#!/usr/bin/env python3
import redis
from collections import Counter
r = redis.Redis(host='localhost', port=6379, db=0,charset="utf-8", decode_responses=True)
import json

hdict = {}
for k,v in r.hgetall('cksum').items():
    v = json.loads(v)
    if k not in hdict:
        hdict[k] = []
    hdict[k].append(v[0])


for k,v in r.hgetall('ignore').items():
    parts = k.split('/')

    if len(parts) > 1:
        if parts[0] == 'data':
            user = parts[1]
    if v not in hdict:
        hdict[v] = []

    hdict[v].append(user)

# k is the hash, l is the list of users associated with the hash
matchSet = {}
for k,l in hdict.items():
    v = set(l)
    #print(l,v)
    if len(v) > 1:
        nameList = list(sorted(list(v)))
        lhs = nameList[0]

        if lhs not in matchSet:
            matchSet[lhs] = {}

        for who in nameList[1:]:
            if who not in matchSet[lhs]:
                matchSet[lhs][who] = 1
            else:
                matchSet[lhs][who] += 1
        
        #print(list(sorted(list(v))))

for k,ma in matchSet.items():
    ma_list = list(ma.keys())
    if len(ma_list) < 6:
        mlist = [k] + ma_list
        for a in ma.keys():
            if a in matchSet:
                ma_list = list(matchSet[a].keys())
                if len(ma_list) < 6:
                    mlist += matchSet[a].keys()

        mlist = list(sorted(set(mlist)))
        print("{} \t {}".format(len(mlist),','.join(mlist)))
        #for who,freq in ma.items():
        #print("{} {:30} {}".format(freq,k,who))
        #print(json.dumps(matchSet))


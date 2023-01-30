#!/usr/bin/env python3
import redis
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

for k,v in hdict.items():
    v = set(v)
    if len(v) > 1:
        print(list(sorted(list(v))))


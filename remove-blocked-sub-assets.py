#!/usr/bin/env python3 
import redis
import os
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

for k,v in r.hgetall('rating').items():
    if float(v) < -3:
        print(k)

toremove = set()
for k,v in r.hgetall('subblock').items():
    if int(v) > 8:
        print(f"sub: {k}")
        toremove.add(k)

for k,v in r.hgetall('subs').items():
    if v in toremove:
        if os.path.exists(k):
            os.remove(k)
            print(k,v)


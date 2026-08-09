#!/usr/bin/env python3 
import redis
import os
import time
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

for k,v in r.hgetall('rating').items():
    if float(v) < -3:
        print(f" {k}")

toremove = set()
for k,v in r.hgetall('subblock').items():
    if int(v) > 6:
        toremove.add(k)

flagSet = set()
skipSet = set()
for k,v in r.hgetall('subs').items():
    if v in toremove:
        if v in skipSet:
            print(f"   Skipping {k} {v}")
            continue

        if os.path.exists(k):

            if v not in flagSet:
                confirm = input(f"remove {v} (y/n/b)? ")
                if "y" in confirm.lower():
                    flagSet.add(v)
                    print(f"Removing {v}")
                else:
                    skipSet.add(v)
                    print(f"   Skipping {v}")
                    continue

            os.remove(k)
            print(f" X Removing {k} {v}")


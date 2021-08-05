#!/usr/bin/env python3
import json,os
def lf(path, kind = 'set'):
    if os.path.exists(path):
        with open(path) as fp:
            if kind == 'json':
                try:
                    return json.load(fp)
                except:
                    return {}

            return set(fp.read().splitlines())

ignore = lf('ignore.json', 'json') or {}
cksum = lf('cksum.json', 'json') or {}
usermap = {}

for k,v in ignore.items():
    parts = k.split('/')
    if len(parts) == 3:
       user = parts[1]

       if user not in usermap:
            usermap[user] = {}

       
       if cksum.get(v) and user != cksum[v][0]:
           print(user,cksum[v])

        # print(cksum[v])
            

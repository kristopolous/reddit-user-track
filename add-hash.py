#!/usr/bin/env python3
import redis
import sys
import json
from PIL import Image
import imagehash
import os
from imagehash import ImageMultiHash
from pprint import pprint
r = redis.Redis(host='lappy.local', port=6379, db=0,charset="utf-8", decode_responses=True)

for line in sys.stdin:
  path1 = line.strip()
  ch1 = r.hget('cr', path1)
  try:
    if not ch1:
        ch1 = imagehash.crop_resistant_hash(Image.open(path1))
        r.hset('cr', path1, str(ch1))
        print("+ {}".format(path1))
  except Exception as ex:
    print("woops, {}".format(ex))
    pass

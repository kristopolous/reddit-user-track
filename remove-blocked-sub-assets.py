!/usr/bin/env python3
import redis
import os
import time
import json

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Configuration for the persistence file
DB_FILE = 'blocked-list.json'

def load_blocked_list():
    """Loads flagged and skipped items from the JSON file."""
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f:
                data = json.load(f)
                # Convert lists to sets for O(1) lookup performance
                flagged = set(data.get('flagged', []))
                skipped = set(data.get('skipped', []))
                return flagged, skipped
        except Exception as e:
            print(f"Error loading {DB_FILE}: {e}")
    return set(), set()

def save_blocked_list(flagged, skipped):
    """Saves the current state of sets to the JSON file."""
    with open(DB_FILE, 'w') as f:
        # JSON doesn't support sets, so we convert them back to lists
        json.dump({"flagged": list(flagged), "skipped": list(skipped)}, f, indent=4)

# Initialize sets from file
flagSet, skipSet = load_blocked_list()

for k,v in r.hgetall('rating').items():
    if float(v) < -3:
        print(f" {k}")

toremove = set()
for k,v in r.hgetall('subblock').items():
    if int(v) > 6:
        toremove.add(k)

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
                    save_blocked_list(flagSet, skipSet) # Save update
                else:
                    skipSet.add(v)
                    print(f"   Skipping {v}")
                    save_blocked_list(flagSet, skipSet) # Save update
                    continue

            os.remove(k)
            print(f" X Removing {k} {v}")

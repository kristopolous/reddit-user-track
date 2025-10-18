#!/usr/bin/env python3 
import praw
import random
import logging
import os
import urllib
import mysecrets
import json
import sys
import pdb
import hashlib
import imagehash
import re
import argparse
import photohash
import subprocess
import redis
import time
from glob import glob
from PIL import Image
from urllib.parse import urlparse
from imgurpython import ImgurClient
from datetime import datetime

start = time.time()
last = start
addurl = lambda urllist, what, entry: urllist.add(f'{what} {entry.subreddit}/{entry.id}')

def ts(w):
    global start, last
    now = time.time()
    print("{:10.4f} {:10.4f} {}".format(now - last, now - start, w))
    last = now

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

logging.basicConfig(level=os.getenv('LOGLEVEL') or 'WARNING')
parser = argparse.ArgumentParser()
parser.add_argument("-f", "--force", help="Force", action='store_true')
parser.add_argument("-g", "--gallery", help="Get the galleries again", action='store_true')
parser.add_argument("-v", "--video", help="Get the video again", action='store_true')
parser.add_argument("-r", "--redgif", help="Get just the redgif again", action='store_true')
args, unknown = parser.parse_known_args()

reddit = praw.Reddit(
    client_id=mysecrets.reddit['pull']['id'], 
    client_secret=mysecrets.reddit['pull']['secret'], 
    password=mysecrets.reddit['pull']['password'], user_agent='test', 
    username=mysecrets.reddit['pull']['username']
)
ts('con:reddit')

gfy_list = ['gfycat.com', 'i.redgifs.com', 'redgifs.com', 'www.redgifs.com']

try:
    imgur = ImgurClient(
        mysecrets.imgur['id'],
        mysecrets.imgur['secret']
    )
except:
    imgur = None
    logging.warning("IMGUR failed to load")

ts('con:img')

def lw(path, what):
    with open(path, 'w') as fp:
        fp.write(str(what))

def lf(path, kind = 'set'):
    if os.path.exists(path):
        with open(path) as fp:
            if kind == 'txt':
                return fp.read()

            if kind == 'json':
                try:
                    return json.load(fp)
                except:
                    return {}

            return set(fp.read().splitlines())

fail = {k:int(v) for k,v in (r.hgetall('fail') or {}).items()}
subblock = lf('subblock.txt') or set()

def get(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'})
    return urllib.request.urlopen(request)


def cksumcheck(path, doDelete=True, who=None):
    filename = os.path.basename(path)
    ihash = r.hget('cksum_rev', "{}/{}".format(who,filename))
    if ihash:
        return ihash

    style = 'md5'
    ext = os.path.splitext(path)[1]

    print("   Summing {}/{}".format(who,path))
    if not os.path.exists(path):
        return False

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

    js = None
    exists = r.hget('cksum',ihash)
    if exists:
        js = json.loads(exists)

    if js and not ( filename in js[1] or js[1] in filename ):
        print("   == {} is {} ".format(filename, exists))
        r.hset('ignore', path, ihash)
        if doDelete:
            os.unlink(path)
        return False
    else:
        r.hset('cksum', ihash, json.dumps([who, filename]))
        r.sadd('cksum_seen', filename)
        r.hset('cksum_rev', "{}/{}".format(who,filename), ihash)


    return ihash

if len(unknown) > 0:
    all = list([m.lower() for m in unknown])

else: 
    with open('userlist.txt') as fp:
        all = sorted(list(set([x[1].strip('/\n ') for x in enumerate(fp)])), key=str.casefold)

if not os.path.isdir('data'):
    os.mkdir('data')

all = list(set([who.lower() for who in all]))
random.shuffle(all)
for who in all:
    who = who.lower()
    content = "data/{}".format(who)

    # if we've made the user path
    if os.path.exists(content):
        # this is O(m*n), hate me later.
        
        existing = list(glob("{}/*[jp][np]g".format(content)))
        for i in range(0, len(existing)):
            ipath = existing[i]
            filename = os.path.basename(ipath)
            cut_path = "{}/{}".format(who,filename)
            is_new = False

            if not r.sismember('cksum_seen', filename):
                ihash = cksumcheck(ipath, who=who)
                is_new = True
            else:
                ihash = r.hget('cksum_rev', cut_path)

            if is_new:
                for j in range(i + 1, len(existing)):
                    jpath = existing[j]
                    filename = os.path.basename(jpath)
                    cut_path = "{}/{}".format(who,filename)

                    jhash = r.hget('cksum_rev',cut_path) or cksumcheck(jpath, who=who)

                    try:
                        dist = photohash.hash_distance(ihash, jhash)
                        if dist < 3:
                            print("{} {} == {}".format(dist, existing[i], existing[j]))
                            r.hset('ignore', ipath, ihash)
                            if os.path.exists(existing[i]):
                                os.unlink(existing[i])
                    except:
                        pass

        for path in glob("{}/*.mp4".format(content)):
            flatten = re.sub('/', '_', path)
            swapped = re.sub('.mp4', '.jpg', flatten)
            path_tn = "tn/{}".format(swapped)

            if os.path.exists(path_tn) and not cksumcheck(path_tn, doDelete=False, who=who):
                os.unlink(path_tn)
                os.unlink(path)

    if fail.get(who) and fail.get(who) > 1:
        print("  -{}".format(who))
        continue

    if not os.path.exists(content):
        print(" / {} (Making dir)".format(who))
        os.mkdir(content)
    else:
        print(" / {}".format(who))


    urllist = set()

    if not args.force:
        urllist = set([x.split(' ')[0] for x in lf("{}/urllist.txt".format(content)) or set()])

    dirty = {}
    mru = lf("{}/mru.txt".format(content), 'txt') or None
    titlelist = lf("{}/titlelist.txt".format(content)) or set()
    entrylist = lf("{}/entrylist.txt".format(content)) or set()
    subredUser = lf("{}/subredditlist.txt".format(content), 'json') or []
    commentMap = lf("{}/commentmap.txt".format(content), 'json') or dict()

    if mru is not None:
        mru = float(mru)
        delta = time.time() - mru
        days = delta / (60 * 60 * 24)
        if days > 21:
            # we want between a 3-73% chance to pull
            # based on the mru
            days_r = 63 - min(62, (days - 21)/3)
            if (random.random() * 100) > days_r:
                logging.warning(f"Skipping {who} - last seen {int(days)} days ago")
                continue
        else:
            logging.warning(f"!!! Pulling {who} - last seen {int(days)} days ago")
    else:
        logging.warning(f"No MRU for {who}")

    ts('pre sub pull')
    try:
        submissions = reddit.redditor(who).submissions.new(limit=25)
    except:
        print("who is {}".format(who))
        continue

    try:
        if who in fail:
            del(fail[who])
            r.hdel('fail', who)

    except:
        if not who in fail:
            fail[who] = 0
        fail[who] += 1
        r.hset('fail', who, fail[who])

        print("Woops, no submissions {} ({})".format(who, fail[who]))

        with open('fail.json', 'w') as f:
            json.dump(fail, f)

        continue

    ts('presub')
    isNew = False
    url_seen = set()

    #print(len(submissions))

    try:
        for entry in submissions:
            if mru is None:
                lw("{}/mru.txt".format(content), entry.created_utc)

            try:
                filename = os.path.basename(entry.url)
            except:
                logging.debug("Couldn't get path for {}".format(entry.url))
                continue

            path = "{}/{}".format(content, filename)

            if r.hget('ignore', filename) or entry.id in entrylist:
                break

            lw("{}/titlelist.txt".format(content), entry.created_utc)
            entrylist.add(entry.id)
            dirty['entry'] = 1

            isNew = True
            parts = urlparse(entry.url)
            url_to_get = entry.url
            titlelist.add(entry.title)
            dirty['title'] = 1

            if r.hget('ignore', path):
                continue

            if parts.netloc in gfy_list:
                if '.' not in path: 
                    path += '.mp4'

            if not entry.url in urllist or (args.redgif and 'redgif' in entry.url) or (args.gallery and 'gallery' in entry.url) or (args.video and 'v.redd' in entry.url):  
                if entry.url in url_seen:
                    continue 

                url_seen.add(entry.url)

                if len(filename) == 0:
                    
                    titlelist.add(entry.selftext)
                    dirty['title'] = 1
                    addurl(urllist, entry.url, entry)
                    dirty['url'] = 1
                    linklist = re.findall(r'http[^\s\])]*', entry.selftext)
                    if len(linklist) > 0:

                        for imgurl in linklist:
                            try:
                                urlparts = urlparse(imgurl)
                            except:
                                logging.warning("Failed to parse url: {}".format(imgurl))
                                continue

                            path = "{}/{}".format(content, os.path.basename(urlparts.path)) 

                            if not os.path.exists(path) and not r.hget('ignore',path):
                                try:
                                    remote = get(imgurl)
                                except:
                                    logging.warning("Cannot grab path {} for text {}".format(imgurl, entry.selftext))
                                    continue

                                addurl(urllist, imgurl, entry)
                                dirty['url'] = 1

                                try:
                                    with open(path, 'bw') as f:
                                        f.write(remote.read())
                                        print("   \_{}".format(path))
                                except:
                                    logging.warning("Can't open path {} for text {} to save {}".format(path, entry.selftext, imgurl))


                    logging.debug("Filename doesn't exist for {}".format(entry.id))
                    continue

                subred = entry.subreddit.display_name

                if subred in subblock:
                    logging.debug("Not grabbing because {} is a blocked sub".format(subred))
                    continue

                subredUser.append([datetime.now().strftime("%Y%m%d"), subred])
                dirty['sub'] = 1

                remote_temp = None
                try:
                    remote_temp = hasattr(entry, 'is_gallery') and entry.is_gallery and entry.gallery_data is not None
                except:
                    logging.warning("Unable to get gallery for user. Might need to wait. Snoozing a bit")
                    time.sleep(2)


                if remote_temp:
                    logging.debug("is a gallery")
                    if os.path.exists(path):
                        print("<< {}".format(path))
                        os.unlink(path)

                    try:
                        items_temp = entry.media_metadata.items()
                    except Exception as ex:
                        logging.warning("Unable to get meta-data: {}".format(ex))
                        items_temp = {}

                    for k,v in items_temp:
                        try:
                            vs = v.get('s') or {}
                            if 'u' in vs:
                                imgurl = vs['u']

                            elif 'gif' in vs:
                                imgurl = vs['gif']

                            else:
                                print("    woops! Can't find an image: {}".format(v['s']))
                                continue
                        except:
                            print("    woops! Can't find an image".format(json.dumps(v)))
                            continue

                        urlparts = urlparse(imgurl)
                        path = "{}/{}".format(content, urlparts.path[1:])

                        try:
                            if not os.path.exists(path) and not r.hget('ignore',path):
                                remote = get(imgurl)
                                addurl(urllist, imgurl, entry)
                                dirty['url'] = 1

                                with open(path, 'bw') as f:
                                    f.write(remote.read())
                                print("   \_{}".format(path))
                        except Exception as ex:
                            logging.warning("Unable to get user: {}".format(ex))
                            
                    addurl(urllist, entry.url, entry)
                    dirty['url'] = 1
                    continue

                print(" \_{}".format(path))

                if hasattr(entry, 'is_video') and entry.is_video and entry.secure_media is not None:
                    url_to_get = entry.secure_media['reddit_video']['fallback_url']

                    # this is a lie, but eh so what
                    path += '.mp4'
                    if os.path.exists(path): 
                        continue
                    print("   \_{}".format(url_to_get))

                elif parts.netloc in ['imgur.com','i.imgur.com']:
                    noext = os.path.splitext(parts.path)[0]
                    pieces = noext.strip('/').split('/')
                    try:
                        if pieces[0] == 'a':
                            for x in imgur.get_album_images(pieces[1]):
                                url_to_get = x.link

                        else:
                            obj = imgur.get_image(pieces[0])
                            url_to_get = obj.link

                    except:
                        print("   \_ Unable to get {}".format(entry.url))
                        r.hset('ignore', path, "na")
                        r.hset('ignore', filename, "na")
                        continue

                    hasext = os.path.splitext(path)
                    if not hasext[1]:
                        ext = os.path.splitext(url_to_get)[1]
                        path += ext

                    print("   \_{}".format(url_to_get))

                elif parts.netloc in gfy_list:
                    url_path = parts.path.split('/')
                    obj = None
                    to_get = url_path[-1]
                    to_get = re.sub('i.redgifs.com/i/([^\.]*).*',r'www.redgifs.com/watch/\1',to_get)
                    to_get = re.sub('.jpg','',to_get)
                    if not os.path.exists(path):
                        url_to_get = entry.url
                        print("   \_{}".format(url_to_get))
                        subprocess.run(['yt-dlp', 'https://redgifs.com/watch/{}'.format(to_get), '-o', path], capture_output=True)
                    addurl(urllist, entry.url, entry)
                    dirty['url'] = 1
                    continue

                try:
                    request = urllib.request.Request(url_to_get, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'})
                    remote = urllib.request.urlopen(request)
                    with open(path, 'bw') as f:
                        f.write(remote.read())

                    addurl(urllist, entry.url, entry)
                    dirty['url'] = 1

                except Exception as ex:
                    print("   woops, can't get {} ({} -> {}): {}".format(entry.url, url_to_get, path, ex))
                    r.hset('ignore', path,  "na")
                    r.hset('ignore', filename, "na")
                    continue
            else:
                logging.debug("Exists: {}".format(filename))

            if not os.path.exists(path):
                attempt = glob("{}.*".format(path))
                if len(attempt) > 0:
                    path = attempt[0]

            if os.path.isfile(path):
                cksumcheck(path, who=who)
    except Exception as ex:
        if ex.response.status_code in [403,404]: 
            print("   \_",ex.response.status_code)
            if not who in fail:
                fail[who] = 0
            fail[who] += 2
            r.hset('fail', who, fail[who])

        continue


    if isNew or mru is None:
        ts('pre comment pull')
        try:
            for entry in reddit.redditor(who).comments.new():
                if mru is None:
                    lw("{}/mru.txt".format(content), entry.created_utc)

                if entry.id in commentMap:
                    break

                commentMap[entry.id] = entry.body
                dirty['comment'] = 1

                subred = entry.subreddit.display_name
                subredUser.append([datetime.now().strftime("%Y%m%d"), subred])
                dirty['sub'] = 1

        except Exception as ex:
            print("comment issues for {} {}".format(who, ex))
            continue


    ts('prefile')
    if dirty.get('comment'):
        with open("{}/commentmap.txt".format(content), 'w') as f:
            json.dump(commentMap, f)

    if dirty.get('entry'):
        with open("{}/entrylist.txt".format(content), 'w') as fp:
            fp.write('\n'.join(list(entrylist)))

    if dirty.get('url'):
        with open("{}/urllist.txt".format(content), 'w') as fp:
            fp.write('\n'.join(list(urllist)))

    if dirty.get('sub'):
        with open("{}/subredditlist.txt".format(content), 'w') as fp:
            json.dump(subredUser, fp)

    if dirty.get('title'):
        with open("{}/titlelist.txt".format(content), 'w') as fp:
            fp.write('\n'.join(list(titlelist)))

ts('done')

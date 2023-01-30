#!/usr/bin/python3 -OO
import praw
import logging
import os
import urllib
import secrets
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
from gfycat.client import GfycatClient
from imgurpython import ImgurClient
import pprint

start = time.time()
last = start
def ts(w):
    global start, last
    now = time.time()
    #print("{:10.4f} {:10.4f} {}".format(now - last, now - start, w))
    last = now

r = redis.Redis(host='localhost', port=6379, db=0,charset="utf-8", decode_responses=True)


parser = argparse.ArgumentParser()
parser.add_argument("-f", "--force", help="Force", action='store_true')
parser.add_argument("-g", "--gallery", help="Get the galleries again", action='store_true')
parser.add_argument("-v", "--video", help="Get the video again", action='store_true')
args, unknown = parser.parse_known_args()

reddit = praw.Reddit(
    client_id=secrets.reddit['pull']['id'], 
    client_secret=secrets.reddit['pull']['secret'], 
    password=secrets.reddit['pull']['password'], user_agent='test', 
    username=secrets.reddit['pull']['username']
)
ts('con:reddit')
gfycat = GfycatClient(
    secrets.gfycat['id'],
    secrets.gfycat['secret']
)
gfy_list = ['gfycat.com', 'i.redgifs.com', 'redgifs.com', 'www.redgifs.com']
ts('con:gfy')

imgur = ImgurClient(
    secrets.imgur['id'],
    secrets.imgur['secret']
)
ts('con:img')


def lf(path, kind = 'set'):
    if os.path.exists(path):
        with open(path) as fp:
            if kind == 'json':
                try:
                    return json.load(fp)
                except:
                    return {}

            return set(fp.read().splitlines())

fail = lf('fail.json', 'json') or {}

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

    print("Summing {}/{}".format(who,path))
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
    all = unknown

else: 
    with open('userlist.txt') as fp:
        all = sorted(list(set([x[1].strip('/\n ') for x in enumerate(fp)])), key=str.casefold)

if not os.path.isdir('data'):
    os.mkdir('data')

for who in all:
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

    if fail.get(who) and fail.get(who) > 3:
        print(" -- {}".format(who))
        continue

    if not os.path.exists(content):
        print(" /{} (Making dir)".format(who))
        os.mkdir(content)
    else:
        print(" /{}".format(who))


    urllist = set()

    if not args.force:
        urllist = lf("{}/urllist.txt".format(content)) or set()

    titlelist = lf("{}/titlelist.txt".format(content)) or set()
    entrylist = lf("{}/entrylist.txt".format(content)) or set()
    subredUser = lf("{}/subreddit.txt".format(content), 'json') or dict()
    commentMap = lf("{}/commentmap.txt".format(content), 'json') or dict()

    ts('pre sub pull')
    try:
        submissions = reddit.redditor(who).submissions.new()
    except:
        print("who is {}".format(who))
        continue

    try:
        if who in fail:
            del(fail[who])

    except:
        if not who in fail:
            fail[who] = 0
        fail[who] += 1

        print("Woops, no submissions {} ({})".format(who, fail[who]))

        with open('fail.json', 'w') as f:
            json.dump(fail, f)

        continue

    ts('presub')
    isNew = False
    try:
        submissions = list(submissions)
    except:
        continue
    for entry in submissions:

        try:
            filename = os.path.basename(entry.url)
        except:
            continue

        if len(filename) == 0:
            continue

        path = "{}/{}".format(content, filename)

        """
        if r.hget('ignore', filename) or entry.id in entrylist:
            break
        """

        entrylist.add(entry.id)

        isNew = True
        parts = urlparse(entry.url)
        url_to_get = entry.url
        titlelist.add(entry.title)

        if r.hget('ignore', path):
            continue

        if parts.netloc in gfy_list:
            if '.' not in path: 
                path += '.mp4'

        if not entry.url in urllist: #or (args.gallery and 'gallery' in entry.url) or (args.video and 'v.redd' in entry.url):  
            subred = entry.subreddit.display_name

            if not subred in subredUser:
                subredUser[subred] = 0

            subredUser[subred] += 1

            if hasattr(entry, 'is_gallery') and entry.is_gallery and entry.gallery_data is not None:
                if os.path.exists(path):
                    print("<< {}".format(path))
                    os.unlink(path)

                for k,v in entry.media_metadata.items():
                    if 'u' in v['s']:
                        imgurl = v['s']['u']

                    elif 'gif' in v['s']:
                        imgurl = v['s']['gif']

                    else:
                        print("    woops! Can't find an image: {}".format(v['s']))
                        continue

                    urlparts = urlparse(imgurl)
                    path = "{}/{}".format(content, urlparts.path[1:])

                    if not os.path.exists(path) and not r.hget('ignore',path):
                        remote = get(imgurl)
                        urllist.add(imgurl)

                        with open(path, 'bw') as f:
                            f.write(remote.read())
                        print("   \_{}".format(path))

                urllist.add(entry.url)
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
                try:
                    to_get = url_path[-1]
                    to_get = re.sub('i.redgifs.com/i/([^\.]*).*',r'www.redgifs.com/watch/\1',to_get)
                    to_get = re.sub('.jpg','',to_get)
                    obj = gfycat.query_gfy(to_get)
                    url_to_get = obj.get('gfyItem').get('mp4Url')

                    if url_to_get is None:
                        url_to_get = obj.get('gfyItem').get('content_urls').get('large').get('url')
                    print("   \_{}".format(url_to_get))

                except Exception as ex:
                    print("   \_ Unable to get {} : {}".format(entry.url, ex))
                    subprocess.run(['youtube-dl', 'https://redgifs.com/watch/{}'.format(to_get), '-o', path], capture_output=True)
                    print("   \_ Got it another way")
                    #    ignore[path] = "na" 
                    urllist.add(entry.url)
                    continue

            try:
                request = urllib.request.Request(url_to_get, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'})
                remote = urllib.request.urlopen(request)
                with open(path, 'bw') as f:
                    f.write(remote.read())

                urllist.add(entry.url)

            except Exception as ex:
                print("   woops, can't get {} ({} -> {}): {}".format(entry.url, url_to_get, path, ex))
                r.hset('ignore', path,  "na")
                r.hset('ignore', filename, "na")
                continue
        else:
            # print("Exists: {}".format(filename))
            pass

        if not os.path.exists(path):
            attempt = glob("{}.*".format(path))
            if len(attempt) > 0:
                path = attempt[0]

        if os.path.exists(path):
            cksumcheck(path, who=who)

    if isNew:
        ts('pre comment pull')
        try:
            for entry in reddit.redditor(who).comments.new():
                if entry.id in commentMap:
                    break

                commentMap[entry.id] = entry.body

                subred = entry.subreddit.display_name
                if not subred in subredUser:
                    subredUser[subred] = 0
                subredUser[subred] += 1

        except Exception as ex:
            print("comment issues for {} {}".format(who, ex))
            continue


    ts('prefile')
    with open("{}/commentmap.txt".format(content), 'w') as f:
        json.dump(commentMap, f)

    with open("{}/entrylist.txt".format(content), 'w') as fp:
        fp.write('\n'.join(list(entrylist)))

    with open("{}/urllist.txt".format(content), 'w') as fp:
        fp.write('\n'.join(list(urllist)))

    with open("{}/subreddit.txt".format(content), 'w') as fp:
        json.dump(subredUser, fp)

    with open("{}/titlelist.txt".format(content), 'w') as fp:
        fp.write('\n'.join(list(titlelist)))


for i in ['fail']:
    with open(i + '.json', 'w') as f:
        json.dump(globals().get(i), f)

ts('done')

#!/usr/bin/env python3
import praw
import os
import mysecrets
import json
import sys
import pdb
reddit = praw.Reddit(
    client_id=mysecrets.reddit['pull']['id'], 
    client_secret=mysecrets.reddit['pull']['secret'], 
    password=mysecrets.reddit['pull']['password'], user_agent='test', 
    username=mysecrets.reddit['pull']['username']
)

def lf(path, kind = 'set'):
    if os.path.exists(path):
        with open(path) as fp:
            if kind == 'json':
                return json.load(fp)

            return set(fp.read().splitlines())

sub = sys.argv[1]
data = lf('{}.json'.format(sub), 'json') or {}
linear = open('{}.txt'.format(sub), 'a')

for submission in reddit.subreddit(sub).new():
    if submission.name not in data:
        data[submission.name] = [submission.title, submission.selftext]
        linear.write(submission.title + "\n--\n")
        try:
            linear.write("{}: {}\n".format(submission.author.name, submission.selftext))
        except:
            linear.write("(unknown): {}\n".format(submission.selftext))

    comments = submission.comments;
    comments.replace_more()
    for comment in comments.list():
        if comment.name not in data:

            data[comment.name] = comment.body
            try:
                linear.write("{}: {}\n".format(comment.author.name,comment.body))
            except:
                linear.write("(unknown): {}\n".format(comment.body))

    with open("{}.json".format(sub), 'w') as fp:
        json.dump(data, fp)

linear.close()

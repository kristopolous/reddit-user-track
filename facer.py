#!/usr/bin/env python3
import cv2
import sys
import os
import glob
import json

cascPath = "haarcascade_frontalface_default.xml"
faceCascade = cv2.CascadeClassifier(cascPath)

def lf(path):
    if os.path.exists(path):
        with open(path) as fp:
            try:
                return json.load(fp)
            except:
                return {}

for userPath in sorted(glob.glob('data/*')):
    user = os.path.basename(userPath)
    if not os.path.isdir(userPath):
        continue
    faceMap = lf('data/{}/faces.json'.format(user)) or {}

    print(user, end='', flush=True)
    for imagePath in glob.glob("data/{}/*[jp][np]g".format(user)):
        print('.', end='', flush=True)
        filename = os.path.basename(imagePath)

        if filename in faceMap:
            continue

        try:
            image = cv2.imread(imagePath)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            faces = faceCascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=7,
                minSize=(300, 300),
                flags = cv2.CASCADE_SCALE_IMAGE
            )
            faceMap[filename] = 1 if len(faces) else 0
        except:
            continue

    print('done')

    with open("data/{}/faces.json".format(user), 'w') as fp:
        json.dump(faceMap, fp)

    try:
        faceMaster = lf('facemaster.json') or {}
        faceMaster[user] = sum(faceMap.values()) / len(faceMap.values())

        with open("facemaster.json", 'w') as fp:
            json.dump(faceMaster, fp)
    except: 
        pass

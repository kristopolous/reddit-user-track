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

base = sys.argv[1]

faceMap = lf('data/{}/faces.json'.format(base)) or {}

print(base, end='', flush=True)
for imagePath in glob.glob("data/{}/*[jp][np]g".format(base)):
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
        faceMap[filename] = len(faces)

        """
        print(len(faces), imagePath)
        if len(faces) > 0:
            for (x, y, w, h) in faces:
                cv2.rectangle(image, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.imshow("Faces found", image)
            cv2.waitKey(0)
        """
    except:
        continue

print('done')

with open("data/{}/faces.json".format(base), 'w') as fp:
    json.dump(faceMap, fp)

faceMaster = lf('facemaster.json') or {}
faceMaster[base] = sum(faceMap.values()) / len(faceMap.values())

with open("facemaster.json", 'w') as fp:
    json.dump(faceMaster, fp)


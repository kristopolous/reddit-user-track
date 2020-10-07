#!/usr/bin/env python3
import cv2
import sys

cascPath = "haarcascade_frontalface_default.xml"
faceCascade = cv2.CascadeClassifier(cascPath)

for imagePath in sys.argv[1:]:
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
        if len(faces) > 0:
            print(imagePath)
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



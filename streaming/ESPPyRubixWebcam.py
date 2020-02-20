#    This program pulls images from a webcam and sends the image to 
#    SAS ESP.  ESP uses the image to determine if a rubiks cube is solved
#
#    Images grabbed using OpenCV
#    If the newly grabbed image is changed then the (don't send same image over and over )
#    image is cropped to 224 by 224 (middle of the image) and base64 encoded. 
#    It is then sent to ESP for scoring. 
#
#    ESP uses a Convolutional Neural Network to determine the score. 
#    The score is returned from ESP as an XML string, parsed and displayed on the 
#    webcam screen.  
#
#    This script was developed on python 3.6.  
#    video_capture = cv2.VideoCapture(1)  -- the 1 represents the video camera on your machine.  Please set appropriately. 
# 

#Copyright © 2019, SAS Institute Inc., Cary, NC, USA.  All Rights Reserved.
#SPDX-License-Identifier: Apache-2.0

import esppy
import cv2
import sys, getopt
import numpy as np
import pandas as pd
import threading
import os
import base64
import requests
import xml.etree.ElementTree as etree
import ast
import json
from pathlib import Path
import socket
import time
import math

print (cv2.__version__,"opencv version is: ")

#  parsed input args.  
#print ('Number of arguments:', len(sys.argv), 'arguments.')
#print ('Argument List:', str(sys.argv))
scriptname = str(sys.argv[0])

ESPServerURL = 'http://iotdemo:61000'
outputfile = ''
try:
  opts, args = getopt.getopt(sys.argv[1:],"hi:",["ifile="])
except getopt.GetoptError:
  print ('******* Syntax Error **********')
  print ('Please enter the following syntax:')
  print  (scriptname + ' -i <ESP URL> # example: http://10.10.10.10:55580 ')
  print ('******* Syntax Error **********')
  sys.exit(2)
for opt, arg in opts:
  if opt == '-h':
     print ('******* Help!!! **********')
     print ('Please enter the following syntax:')
     print  (scriptname + ' -i <ESP URL> # example: http://10.10.10.10:55580 ')
     print ('Enter q in webcam window to terminate. ')
     print ('******* Help!!! **********')
     sys.exit()
  elif opt in ("-i", "--ifile"):
     ESPServerURL = arg
print ('Server URL is :', ESPServerURL)

prediction = "-----"
prediction_precentage = ''


imagesendinterval =  25    #  limit blasting ESP with images 
imagesendtime = 0.111

originalwd = os.getcwd()
userID = 'savedimgs'
userFolder = userID
if not os.path.exists(userFolder):
    os.makedirs(userFolder)
cwd = os.getcwd()   # current working directory

def ESPsend(serial, userID, data):
    global imagesendtime
    global prediction
    global prediction_precentage
    if (imagesendtime + imagesendinterval) < time.time():  # Don't send unless last send complete.
        #filename = 'filetest' + prediction +str(i) + '.jpg'
        #cv2.imwrite(filename, data, [cv2.IMWRITE_JPEG_QUALITY, 95])
        prediction = 'Processing'
        prediction_precentage = ''
        ret, img = cv2.imencode('.jpg', data)
        
        try:
            cv2.destroyWindow('Snap!')   #  remove old snapshot when prediction comes back. 
        except cv2.error as e:
            pass
        cv2.imshow("Snap!",data)  #  new snapshot that is sent to ESP 
        
        imgbytes = base64.b64encode(img)
        imgStr = str(imgbytes)  
        imgStr = imgStr[2:-1]  # this has a b'lsklsdk'  in front.  remove b and quotes. 
        
        insert = 'i'
        normal = 'n'
        newline = "\n"
        sep = ","
        seq = (insert,normal,"",imgStr,newline)
        csv = sep.join(seq)
        
        userID = userID 
        #print ("---send data to ESP ---",time.time())
        dest.send(csv)  # send image to ESP 
        imagesendtime = time.time()   # track send time

    return
    
def on_score_event(socketobj,xmlmsg):  # process score events from ESP
    global prediction
    global prediction_precentage
    global imagesendtime
    localimagesendtime = time.time() - imagesendtime  # calculate round trip time. 
    localimagesendtime=float("{0:.2f}".format(localimagesendtime))  # round to 2 decimal places. 
    imagesendtime = 0  #  reset this so a new send can happy asap. 
    imagesendtime = time.time() - imagesendinterval + 1   # reset this so a new send can happen asap.
    
    
        
    #print (xmlmsg) 
    tree  = etree.fromstring(xmlmsg)
    for branch in tree.iter('event'):
        prediction2 = branch.find('I__label_').text
        Precentgood = branch.find('P__label_good').text
        Precentbad = branch.find('P__label_bad').text
        Precentempty = branch.find('P__label_empty').text
        
        
    prediction = prediction2
    prediction = ' '.join(filter(None,prediction.split(' ')))   # filter out white space 
    if prediction == 'good':
        prediction_precentage = str(math.floor(float(Precentgood)* 100 )) + "%"
    elif prediction == 'bad':    
        prediction_precentage = str(math.floor(float(Precentbad)* 100 )) + "%"
    else:
        prediction_precentage = str(math.floor(float(Precentempty)* 100 )) + "%"
    print (prediction,prediction_precentage,"-score durration-  " ,localimagesendtime ,' seconds' )
    return 
    

esp = esppy.ESP(ESPServerURL)
projects = esp.get_projects()
project = projects['prog1']
source = project.queries['CQ'].windows['image']
scored = project.queries['CQ'].windows['imageScoring']
dest = source.create_publisher(blocksize = 1, rate = 0, pause = 0, dateformat= '%Y-%m-%d%20%H:%M:%S', opcode = 'insert', format = 'csv')

finalDest = project.queries['CQ'].windows['imageScoring']
#finalDest.subscribe()   # subscribe to output from scoring window. 


sub2 =  finalDest.create_subscriber(mode='streaming',on_message=on_score_event,pagesize=5)   # subscribe to output from scoring window. 
sub2.start()

#video_capture = cv2.VideoCapture(0)
video_capture = cv2.VideoCapture(1)

serial = 0
bars = ''

def mse(imageA, imageB):
    # the 'Mean Squared Error' between the two images is the
    # sum of the squared difference between the two images;
    # NOTE: the two images must have the same dimension
    err = np.sum((imageA.astype("float") - imageB.astype("float")) ** 2)
    err /= float(imageA.shape[0] * imageA.shape[1])
    err = math.floor(err)
    # return the MSE, the lower the error, the more "similar"
    # the two images are
    return err

while True:
    
    serial = serial + 1 
    
    time.sleep(.1)  # breathe
    ret, frame = video_capture.read()  # Capture frame-by-frame
    img = frame  
    y=0 
    height, width, channels = img.shape
    Xoffset =  math.floor((width - height ) / 2)
    img=img[y:y+height,Xoffset:Xoffset + height]    #  make this img a square from the center of the image.   
    
    if serial > 1:
        data2 = data.copy()
    data = cv2.resize(img, (224, 224), interpolation=cv2.INTER_CUBIC)   # resize to 224 
    
    #  Check if 2 images are equals
    if serial > 1:
        difference = mse(data, data2)  #  calculate the Mean Square Error between the 2 images. 
        #print (difference,  "MSE between images. ")
        if difference < 100:
            #print("The images are completely Equal") 
            hi=None
        else:
            ESPsend(serial,userID, data)   #  send new image to ESP for scoring.  
    else:
        ESPsend(serial,userID, data)
        
    if prediction == 'bad':  #  set colors  red
            blue = 5
            green = 0
            red = 255
            bars = ' - - - '
    elif prediction == 'good':    #  green 
            blue = 5
            green = 255
            red = 0        
            bars = ' - - - '
    elif prediction == 'empty':  # blue 
            blue = 245
            green = 5
            red = 5        
            bars = ' - - - '        
    elif prediction == 'Processing':   # white 
            blue = 240
            green = 240
            red = 240
            if (serial % 10 ) == 0: 
                bars = ' - - - '
            elif (serial % 5 ) == 0:    
                bars = '  '
    else: 
            blue = 240
            green = 240
            red = 240
            bars = '' 
    
    
    cv2.putText(frame, prediction + bars + prediction_precentage, (20,380), cv2.FONT_HERSHEY_SIMPLEX, 1, (blue, green, red), 2)
    # Display the resulting frame
    cv2.imshow('Video', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# When everything is done, release the capture
video_capture.release()
cv2.destroyAllWindows()

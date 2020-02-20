#    This program pulls images from a webcam and writes them to a directory
#    This script was developed on python 3.6.  

#Copyright © 2019, SAS Institute Inc., Cary, NC, USA.  All Rights Reserved.
#SPDX-License-Identifier: Apache-2.0

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
    
outdir = 'good'
outdir = 'empty'
outdir = 'bad'
allowdups = False  # prevent duplicate frames to be written
writefiles = False
try:
  opts, args = getopt.getopt(sys.argv[1:],"hi:dg",["ifile=",'dups','go'])
except getopt.GetoptError:
  print ('******* Syntax Error **********')
  print ('******* Syntax Error **********')
  print  ('Please enter: ' + scriptname + ' -h for help.  ')
  print ('******* Syntax Error **********')
  print ('******* Syntax Error **********')
  sys.exit(2)
for opt, arg in opts:
  if opt == '-h':
     print ('******* Help!!! **********')
     print ('Please enter the following syntax:')
     print  (scriptname + ' -i <directory name> # example: good ')
     print  (scriptname + ' -d or --dups  to allow duplicate images to be written ')
     print  (scriptname + ' -g or --go Start image collection now')
     print ('Enter q in webcam window to terminate. ')
     print ('Enter g in webcam window to start frame capture. ')
     print ('Enter s in webcam window to stop frame capture. ')
     print ('******* Help!!! **********')
     sys.exit()
  elif opt in ("-i", "--ifile"):
     outdir = arg
  elif opt in ("-d", "--dups"):
    print("Duplicate images are now allowed")
    allowdups = True
  elif opt in ("-g" , "--go"):
    print("Image collection starts now!")
    writefiles = True  

breathe = 1.1 
imagesendinterval =  25    #  limit blasting ESP with images 
imagesendtime = 0.111

originalwd = os.getcwd()

if not os.path.exists(outdir):
    os.makedirs(outdir)
cwd = os.getcwd()   # current working directory
print ("current working directory", cwd )
print("Files will be written to directory:", outdir)

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

print("Initializing  ........")
video_capture = cv2.VideoCapture(0)

serial = 0


ret, frame = video_capture.read()  # Capture a frame 
previousframe = frame 
print ('Enter q in webcam window to terminate. ')
print ('Enter g in webcam window to start frame capture. ')
print ('Enter s in webcam window to stop frame capture. ')
while True:
    previousframe = frame 
    #time.sleep(breathe)     # so framerate. 
    time.sleep(1.1)     # slow framerate. 
    ret, frame = video_capture.read()  # Capture frame-by-frame
    img = frame
    filename = cwd +'/'+ outdir +'/'+ outdir + str(serial) + '.jpg'
    
    if allowdups == True:
        duplicate=False
    else:
        #  Check if 2 images are equals
        #difference = cv2.subtract(original, image_to_compare)
        #b, g, r = cv2.split(difference)
        difference = mse(frame, previousframe)  #  calculate the Mean Square Error between the 2 images. 
        #print (difference,  "MSE between images. ")
        if difference < 400:
            #print("The images are completely Equal") 
            duplicate=True 
        else:
            duplicate=False
    
    if writefiles and (not duplicate):
        serial = serial + 1 
        y=0 
        height, width, channels = img.shape
        Xoffset =  math.floor((width - height ) / 2)
        img=img[y:y+height,Xoffset:Xoffset + height]    #  make this img a square from the center of the image.   
        img = cv2.resize(img, (224, 224), interpolation=cv2.INTER_CUBIC)   # resize to 224 
        print (filename, "written to disk ")
        
        cv2.imwrite(filename, img, [cv2.IMWRITE_JPEG_QUALITY, 95])   # write file.  
    # Display the resulting frame
    cv2.imshow('Video', frame)            
    
    keyboardinput = cv2.waitKey(1)
    # waitkey returns an ASCII value only in the last 8 bits. 
    # To use it to compare with a char first mask everything but 
    # the first 8 bits and then convert it using the chr builtin method of Python
    key = chr(keyboardinput & 255)  #  mask and convert ascii to character
    if key == 'q':   # quit 
        break
    elif key == 'g':    #  start writing files.   
        print("Image collection started!")
        writefiles = True 
    elif key == 's':    #  stop writing files
        print("Image collection stopped!")
        writefiles = False
    else:
        key = None
        #print ('key in else stmt', key )

# When everything is done, release the capture
video_capture.release()
cv2.destroyAllWindows()

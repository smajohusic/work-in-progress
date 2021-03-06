import face_recognition
import os
import configparser
import time
import RPi.GPIO as GPIO
import picamera
import numpy as np
from firebaseHelper import (init, updateCurrentUser)

# Initilize and set the GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(11, GPIO.IN) #Read output from PIR motion sensor
GPIO.setup(3, GPIO.OUT) #LED output pin

def recognizeForAmount():
    minutes = getConfig('recognition', 'minutesToRecognize') #returns minutes
    return int(minutes) * 60000 # convert to ms

def getConfig(section, name):
    config = configparser.ConfigParser()
    config.read('../config/config.txt')
    return config.get(section, name)

def getImages():
    currentPath = os.path.dirname(os.path.abspath(__file__)) # Absolute dir the script is in
    filepath = "../images/" # The path where the pictures are uploaded
    directory = os.listdir(os.path.join(currentPath, filepath))
    images = [ fi for fi in directory if fi.endswith(('.JPG', '.jpg', 'jpeg', '.JPEG')) ]
    return images

def resolveUserId(name):
    if name.find("#") != -1:
        return int(name.split("#")[1][:1])

# Directory to images
images = getImages()

#For name to store
known_person = []

#Current user id
userId = None

#For Images
known_image = []

#ForEncoding
known_face_encoding = []

print("Getting all images")

for file in images:
    try:
        known_person.append(file.replace(".jpg", ""))
        file=os.path.join('../images/', file)
        known_image = face_recognition.load_image_file(file)
        known_face_encoding.append(face_recognition.face_encodings(known_image)[0])
    except Exception as e:
        pass

print("Ready for face recognition")

def recognizeFace():
    # Initialize some variables
    face_locations = []
    face_encodings = []
    face_names = []
    process_this_frame = 0
    minutesToRecognize = recognizeForAmount()

    # Get a reference to the Raspberry Pi camera.
    camera = picamera.PiCamera()
    camera.resolution = (480, 368)
    camera.brightness = 75
    camera.contrast = 60
    camera.vflip = True
    output = np.empty((368, 480, 3), dtype=np.uint8)

    # Currently used for debugging
    camera.start_preview()

    while time.sleep(minutesToRecognize):
        # Grab a single frame of video from the RPi camera as a numpy array
        camera.capture(output, format="rgb")

        # Only process every other frame of video to save time
        if process_this_frame%5==0:
            # Find all the faces and face encodings in the current frame of video
            face_locations = face_recognition.face_locations(output)
            face_encodings = face_recognition.face_encodings(output, face_locations)

            face_names = []

            for face_encoding in face_encodings:
                match = face_recognition.compare_faces(known_face_encoding, face_encoding)
                matches=np.where(match)[0] #Checking which image is matched

                if len(matches)>0:
                    camera.stop_preview()
                    # Destroy the camera
                    camera.close()

                    name = str(known_person[matches[0]])
                    face_names.append(name)
                    userId = resolveUserId(name)
                else:
                    face_names.append("Unknown")

        process_this_frame =  process_this_frame+1
        if process_this_frame>5:
            process_this_frame=0

    camera.stop_preview()

    # Destroy the camera
    camera.close()

    print("Done recognizing faces")

    # After the amount of time has passed, start detecting motion again
    detectMotion()

def detectMotion():
    detect = True
    last_motion = 0

    while detect:
        try:
            input = GPIO.input(11)

            if input == 1:
                last_motion = time.time()

                if time.time() - last_motion <= 7:
                    # Stop detecting motion
                    detect = False
                    # Start recognizing faces
                    recognizeFace()

                time.sleep(1)
        except KeyboardInterrupt:
            break

# Start detecting motion
detectMotion()
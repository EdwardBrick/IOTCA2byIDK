# Import SDK packages
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from time import sleep
from gpiozero import MCP3008, LED, Buzzer
from rpi_lcd import LCD
from picamera import PiCamera
import boto3
import botocore
import datetime as datetime
import RPi.GPIO as GPIO
import MFRC522
import sys
import Adafruit_DHT
import signal
import json
import time

pin = 4
led = LED(18)
lcd = LCD()
ledOK = LED(24)
bz = Buzzer(23)
adc = MCP3008(channel=0)
s3 = boto3.resource('s3')
uid = None
prev_uid = None 
continue_reading = True
full_path = '/home/pi/Desktop/image1.jpg'
file_name = 'image1.jpg'
bucket = 'sp-p1828881-s3-bucket'
exists = True
camera = PiCamera()

print("Program is running")

#s3 = boto3.resource('s3',
    #aws_access_key_id="ASIAXFURNDPUN6ZO6U5K",
    #aws_secret_access_key= "o9P15rHnWstVdRuvtSWSANW7NtdS1TUtFNYJJ8ot")
#print("S3 credentials initialized")

try:
    s3.meta.client.head_bucket(Bucket=bucket)
except botocore.exceptions.ClientError as e:
    error_code = int(e.response['Error']['Code'])
    if error_code == 404:
        exists = False

if exists == False:
  s3.create_bucket(Bucket=bucket,CreateBucketConfiguration={
    'LocationConstraint': 'us-east-1'})

# Capture SIGINT for cleanup when the script is aborted
def end_read(signal,frame):
    global continue_reading
    print "Ctrl+C captured, ending read."
    continue_reading = False
    GPIO.cleanup()
    
def takePhotoWithPiCam():
    camera.capture(full_path)
    
# Hook the SIGINT
signal.signal(signal.SIGINT, end_read)
print("Signal hooked")

# Create an object of the class MFRC522
mfrc522 = MFRC522.MFRC522()
print("mfrc522 created")

# Custom MQTT message callback
def customCallback(client, userdata, message):
	print("Received a new message: ")
	print(message.payload)
	print("from topic: ")
	print(message.topic)
	print("--------------\n\n")
	
host = "amitv187sde3m-ats.iot.us-east-1.amazonaws.com"
rootCAPath = "rootca.pem"
certificatePath = "certificate.pem.crt"
privateKeyPath = "private.pem.key"
print("certificates initialized")

my_rpi = AWSIoTMQTTClient("PubSub-1828881")
my_rpi.configureEndpoint(host, 8883)
my_rpi.configureCredentials(rootCAPath, privateKeyPath, certificatePath)

my_rpi.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
my_rpi.configureDrainingFrequency(2)  # Draining: 2 Hz
my_rpi.configureConnectDisconnectTimeout(10)  # 10 sec
my_rpi.configureMQTTOperationTimeout(5)  # 5 sec
print("MQTT Configured")

# Connect and subscribe to AWS IoT
my_rpi.connect()
print("rpi connected")

my_rpi.subscribe("sensors/light", 1, customCallback)
print("rpi subcribed")
sleep(2)

# Publish to the same topic in a loop forever
loopCount = 0
while True:
    # Init LEDs

    led.on()
    ledOK.off()
    bz.off()

    # Scan for cards    
    (status,TagType) = mfrc522.MFRC522_Request(mfrc522.PICC_REQIDL)

    
    print("Scanning for cards")
    lcd.text('Scanning', 1)
    loopCount = loopCount+1


    # If a card is found
    if status == mfrc522.MI_OK:
    
        print("status ok")
        lcd.text('Welcome', 1)

        ledOK.on()
        bz.on()
        led.off()
        takePhotoWithPiCam()
        bz.off()
        s3.Object(bucket, file_name).put(Body=open(full_path, 'rb'))
        print("File uploaded")
        
        # Get the UID of the card
        (status,uid) == mfrc522.MFRC522_Anticoll()
        print(mfrc522.MFRC522_Anticoll())
        if uid!=prev_uid:
            prev_uid = uid
            message = ("New card detected! UID of card is {}".format(uid))
            message2 = {}
            message2["deviceid"]="deviceid_dariuschoo"

            now = datetime.datetime.now()
            message2["datetimeid"] = now.isoformat()      
            message2["value"] = message
            #message2[]
            
            #temperature = Adafruit_DHT.read_retry(11, pin)
            #print('Temp: {:.1f} C'.format(float(temperature)))
            #message2["Temperature"] = 'Temp: {:.1f} C'.format(float(temperature))

            my_rpi.publish("sensors/light", json.dumps(message2), 1)
            sleep(1)

    
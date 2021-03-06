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
import telepot
import sys
import Adafruit_DHT
import MFRC522
import signal
import json
import time

my_bot_token = '863095732:AAEehVDL5E-UeKPJw-jRsuuUuZhLTx0fRMA'
pin = 4
led = LED(18)
lcd = LCD()
ledOK = LED(24)
bz = Buzzer(23)
s3 = boto3.resource('s3')
adc = MCP3008(channel=0)
uid = None
prev_uid = None 
continue_reading = True
full_path = '/home/pi/Desktop/image1.jpg'
file_name = 'image1.jpg'
bucket = 'sp-p1828881-s3-bucket'
exists = True
camera = PiCamera()
isATSOn = True

print("Program is running")

# Capture SIGINT for cleanup when the script is aborted
def end_read(signal,frame):
    global continue_reading
    print "Ctrl+C captured, ending read."
    continue_reading = False
    GPIO.cleanup()
    
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
    
def onATS():
    global isATSOn
    isATSOn = True
    return "Got it, ATS is now turned on"
    
def offATS():
    global isATSOn 
    isATSOn = False
    return "Got it, ATS is now turned off"
    
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
	
def respondToMsg(msg):
    chat_id = msg['chat']['id']
    command = msg['text']
    print('Got command:{}'.format(command))
    if command == 'offATS':
        bot.sendMessage(chat_id, offATS())
    if command == 'onATS':
        bot.sendMessage(chat_id, onATS())
    
host = "amitv187sde3m-ats.iot.us-east-1.amazonaws.com"
rootCAPath = "rootca.pem"
certificatePath = "certificate.pem.crt"
privateKeyPath = "private.pem.key"
print("certificates initialized")

bot = telepot.Bot(my_bot_token)
bot.message_loop(respondToMsg)
print('Listening for RPI Commands')

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
    while isATSOn == True:
        # Init LEDs
        print (isATSOn)
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
            ledOK.on()
            bz.on()
            led.off()
            bz.off()
            lcd.text('Welcome', 1)
                
            # Get the UID of the card
            (status,uid) = mfrc522.MFRC522_Anticoll()
            message = ("New card detected! UID of card is {}".format(uid))
            message2 = {}
            message2["deviceid"]="deviceid_dariuschoo"

            now = datetime.datetime.now()
            message2["datetimeid"] = now.isoformat()      
            message2["value"] = message
            #message2[]
                
            humidity, temperature = Adafruit_DHT.read_retry(11, pin)
            message2["temperature"] = temperature
            print(temperature)
                

            my_rpi.publish("sensors/light", json.dumps(message2), 1)
                
            takePhotoWithPiCam()
            s3.Object(bucket, file_name).put(Body=open(full_path, 'rb'))
            print("File uploaded")
                
            sleep(1)
                
    while isATSOn == False:
        # Init LEDs
        led.on()
        ledOK.off()
        lcd.text('No ATS', 1)
        sleep(1)
    
from  AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTShadowClient
import random, time, datetime, os

# A random programmatic shadow client ID.
SHADOW_CLIENT = "Pi_A0125958R_A0179701B"

# The unique hostname that &IoT; generated for 
# this device.
HOST_NAME = "a1xli7oxtwsplh-ats.iot.us-west-2.amazonaws.com"

# The relative path to the correct root CA file for &IoT;, 
# which you have already saved onto this device.
ROOT_CA = "AmazonRootCA1.pem"

# The relative path to your private key file that 
# &IoT; generated for this device, which you 
# have already saved onto this device.
PRIVATE_KEY = "2b35f1588c-private.pem.key"

# The relative path to your certificate file that 
# &IoT; generated for this device, which you 
# have already saved onto this device.
CERT_FILE = "2b35f1588c-certificate.pem.crt"

# A programmatic shadow handler name prefix.
SHADOW_HANDLER = "Pi_A0125958R_A0179701B"

# Automatically called whenever the shadow is updated.
def myShadowUpdateCallback(payload, responseStatus, token):
  print()
  print('UPDATE: $aws/things/' + SHADOW_HANDLER + 
    '/shadow/update/#')
  print("payload = " + payload)
  print("responseStatus = " + responseStatus)
  print("token = " + token)

# Create, configure, and connect a shadow client.
myShadowClient = AWSIoTMQTTShadowClient(SHADOW_CLIENT)
myShadowClient.configureEndpoint(HOST_NAME, 8883)
myShadowClient.configureCredentials(ROOT_CA, PRIVATE_KEY,
  CERT_FILE)
myShadowClient.configureConnectDisconnectTimeout(10)
myShadowClient.configureMQTTOperationTimeout(5)
myShadowClient.connect()
myShadowClient.disconnect()
myShadowClient.connect()
# Create a programmatic representation of the shadow.
myDeviceShadow = myShadowClient.createShadowHandlerWithName(
  SHADOW_HANDLER, True)

def get_temp():
    temp = os.popen("vcgencmd measure_temp").readline()
    return (temp.replace("temp=",""))

# *****************************************************
# Main script runs from here onwards.
# To stop running this script, press Ctrl+C.
# *****************************************************

# Get the labels out
sensor_name = ['Temp'+ str(i) for i in range(1,2)]
dataLabels = ['id', 'timestamp', 'matricNumber'] + sensor_name

matricNumber = 'A0125958R_A0179701B'

for i in range(0,len(dataLabels)):
    dataLabels[i] = '\"' + dataLabels[i] + '\"'


dataString = []
modifiedData = []

head = '{"state":{"reported":{'
tail = '}}}'
count = 0

while True:
    
    temp = get_temp()
    temp = temp[0:4]
    print(temp)
    count = count+1
    print(count);
    
    modifiedData = []
    modifiedData.append(str('Raspberry' + 'Pi'))
    modifiedData.append(str(datetime.datetime.utcnow()))
    modifiedData.append(matricNumber)
    for j in range(2,len(sensor_name)):
        modifiedData.append(temp)      
    
    ColumnLabels = []
    ColumnLabels.append(str(dataLabels[0] + ':'))
    ColumnLabels.append(str('"' + modifiedData[0] + '",'))
    ColumnLabels.append(str(dataLabels[1] + ':'))
    ColumnLabels.append(str('"' + str(datetime.datetime.now()) + '",'))
    ColumnLabels.append(str(dataLabels[2] + ':'))
    ColumnLabels.append(str('"' + matricNumber + '",'))
    
   
    for i in range(3,len(dataLabels)):
        ColumnLabels.append(str(dataLabels[i] + ':'))
        ColumnLabels.append(str('"' + temp + '",'))
    
    string = ''.join(ColumnLabels)
    string = string[:-1]
    
    data = []
    data.append(head)
    data.append(string)
    data.append(tail)
    data.append('\n')
    dataString = ''.join(data)
    print(dataString)
    myDeviceShadow.shadowUpdate(dataString,myShadowUpdateCallback, 5)
    
    time.sleep(5)
    if count>2000:break

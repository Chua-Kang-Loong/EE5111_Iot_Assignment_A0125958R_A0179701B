from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTShadowClient
import random, time, datetime

# A random programmatic shadow client ID.
SHADOW_CLIENT = "EE5111_Thing1_A0125958R_A0179701B"

# The unique hostname that &IoT; generated for 
# this device.
HOST_NAME = "aekkzs6upiibj-ats.iot.ap-southeast-1.amazonaws.com"

# The relative path to the correct root CA file for &IoT;, 
# which you have already saved onto this device.
ROOT_CA = "AmazonRootCA1.pem"

# The relative path to your private key file that 
# &IoT; generated for this device, which you 
# have already saved onto this device.
PRIVATE_KEY = "46de85e2bd-private.pem.key"

# The relative path to your certificate file that 
# &IoT; generated for this device, which you 
# have already saved onto this device.
CERT_FILE = "46de85e2bd-certificate.pem.crt"

# A programmatic shadow handler name prefix.
SHADOW_HANDLER = "EE5111_Thing1_A0125958R_A0179701B"

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

# Create a programmatic representation of the shadow.
myDeviceShadow = myShadowClient.createShadowHandlerWithName(
  SHADOW_HANDLER, True)

# *****************************************************
# Main script runs from here onwards.
# To stop running this script, press Ctrl+C.
# *****************************************************

infile = open('train_FD001.txt','r')
outfile = open('train_FD001','a')

# Declare all Data Labels
sensor_name = ['s'+ str(i) for i in range(1,22)]
dataLabels = ['id', 'timestamp', 'Matric_Number', 'te', 'os1', 'os2', 'os3'] + sensor_name

matricNumber = 'A0125958R_A0179701B'

for i in range(0,len(dataLabels)):
    dataLabels[i] = '\"' + dataLabels[i] + '\"'

# Split Columns from FD001.txt files to columns
for line in infile.readlines():
    outfile.write(line)
    
process = open("train_FD001",'r')

dataString = []
modifiedData = []

head = '{"state":{"reported":{'
tail = '}}}'
# Read data, Add additional texts and Send out messages
for x in process.readlines():
    newData = x.split(" ")
    modifiedData = []
    modifiedData.append(str('FD001_' + newData[0]))
    modifiedData.append(str(datetime.datetime.utcnow()))
    modifiedData.append(matricNumber)
    for j in range(2,len(sensor_name)):
        modifiedData.append(newData[j])      
    
    ColumnLabels = []
    ColumnLabels.append(str(dataLabels[0] + ':'))
    ColumnLabels.append(str('"' + modifiedData[0] + '",'))
    ColumnLabels.append(str(dataLabels[1] + ':'))
    ColumnLabels.append(str('"' + str(datetime.datetime.now()) + '",'))
    ColumnLabels.append(str(dataLabels[2] + ':'))
    ColumnLabels.append(str('"' + matricNumber + '",'))
    
   
    for i in range(3,len(dataLabels)):
        ColumnLabels.append(str(dataLabels[i] + ':'))
        ColumnLabels.append(str('"' + newData[i-2] + '",'))
    
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
    
    time.sleep(10)

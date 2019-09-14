#!/usr/bin/env python
# coding: utf-8
# In[]: Import Library
import os
import boto3
import re
import copy
import time
import json
import csv
import numpy as np
from time import gmtime, strftime
from sagemaker import get_execution_role
from matplotlib import pyplot as plt
import sagemaker
from sagemaker.amazon.amazon_estimator import get_image_uri


# In[]:

# Data download from https://climate.nasa.gov/vital-signs/sea-level/
# Lets perform the data preparation
f = open('GMSL_TPJAOS_4.2_199209_201906.txt', 'r') 
data = csv.reader(f,delimiter='\t')

train_key      = 'ee5111_training.json'
test_key       = 'ee5111_test.json'
dataset={}
x=[]
y=[]
count=1
prevYear=0
init_level=-37.55
minYear  = 1993
maxYear  = 2018
prediction_length = 1
for row in data:
        # Remove empty strings caused by multiple spaces between columns
        row = list(filter(None, row))
        
        year=row[2]
        slevel=float(row[11])-init_level
        year = year[0:4] 
        slevel = round(slevel, 4)
        # Data for plotting
        # x list=counter, y list=sealevel
        x.append(count)
        y.append(float(slevel))
        count=count+1
        
        # Data for training
        # dictionary: key=year, value=list of ordered daily sealevel
        if (year != prevYear):
            dataset[year]=[]
            prevYear=year
        dataset[year].append(float(slevel))
print(y)        
nb_samples_per_year = list(map(lambda x: len(x), (dataset[str(year)] for year in range(minYear, maxYear+1))))
nb_samples_per_year = np.unique(nb_samples_per_year).tolist()

fig=plt.figure(figsize=(64, 16))
plt.plot(x,y)
plt.show()

trainingSet = dataset.copy()
del trainingSet["2019"] 
testSet = dataset.copy()

def writeDataset(filename, data): 
    file=open(filename,'w')
    for year in data.keys():
        # One JSON sample per line
        line = "\"start\":\"{}\", \"target\":{}".format(year,data[year])  # this the require deepar input format
        file.write('{'+line+'}\n')

writeDataset(train_key, trainingSet)        
writeDataset(test_key, testSet)


# In[]::


role = get_execution_role()
region = boto3.Session().region_name
bucket='pi.a0125958r.a0179701b' # Replace with your s3 bucket name
prefix = 'SageMaker' # Used as part of the path in the bucket where you store data
bucket_path = 'https://s3-{}.amazonaws.com/{}'.format(region,bucket) # The URL to access the bucket

train_prefix   = '{}/{}'.format(prefix, 'train')
test_prefix    = '{}/{}'.format(prefix, 'test')
output_prefix  = '{}/{}'.format(prefix, 'output')
sagemaker_session = sagemaker.Session()

train_path  = sagemaker_session.upload_data(train_key, bucket=bucket, key_prefix=train_prefix)
test_path   = sagemaker_session.upload_data(test_key,  bucket=bucket, key_prefix=test_prefix)

s3_output_location = 's3://pi.a0125958r.a0179701b/SageMaker'.format(bucket, prefix, 'deepar')
print(train_path)


# In[]:



containers = {
    'us-east-1': '522234722520.dkr.ecr.us-east-1.amazonaws.com/forecasting-deepar:latest',
    'us-east-2': '566113047672.dkr.ecr.us-east-2.amazonaws.com/forecasting-deepar:latest',
    'us-west-2': '156387875391.dkr.ecr.us-west-2.amazonaws.com/forecasting-deepar:latest',
    'eu-west-1': '224300973850.dkr.ecr.eu-west-1.amazonaws.com/forecasting-deepar:latest'
}

image_name = containers[region]

estimator = sagemaker.estimator.Estimator(
    sagemaker_session=sagemaker_session,
    image_name=image_name,
    role=role,
    train_instance_count=1,
    train_instance_type='ml.c4.8xlarge',
    base_job_name='EE5111',
    output_path=s3_output_location
)


# In[]:


prediction_length = 7
hyperparameters = {
    "time_freq": 'W', # weekly series
    "context_length": prediction_length,
    "prediction_length": prediction_length, # number of data points to predict
    "num_cells": "40",
    "num_layers": "3",
    #"likelihood": "gaussian",
    "epochs": "200",
    "mini_batch_size": "32",
    "learning_rate": "0.001",
    "dropout_rate": "0.05",
    "early_stopping_patience": "10" # stop if loss hasn't improved in 10 epochs
}

estimator.set_hyperparameters(**hyperparameters)


# In[]::


data_channels = {"train": train_path, "test": test_path}


# In[]:


estimator.fit(inputs=data_channels,  logs=True)


# In[]:



job_name = estimator.latest_training_job.name

endpoint_name = sagemaker_session.endpoint_from_job(
    job_name=job_name,
    initial_instance_count=1,
    instance_type='ml.m4.xlarge',
    deployment_image=image_name,
    role=role
)

predictor = sagemaker.predictor.RealTimePredictor(
    endpoint_name, 
    sagemaker_session=sagemaker_session, 
    content_type="application/json")


# In[]:


q1 = '0.1'         # compute p10 quantile
q2 = '0.9'         # compute p90 quantile
num_samples = 50  # predict 50 sample series
    
def buildPredictionData(year, data):
    year_temps = data[str(year)][-prediction_length:]
    s = {"start": "{}-01-01 00:00:00".format(year), "target": year_temps}
    series = []
    series.append(s)
    configuration = {
        "output_types": ["mean", "quantiles", "samples"],
        "num_samples": num_samples,
        "quantiles": [q1, q2]
    
    }
    http_data = {
        "instances": series, 
        "configuration": configuration
    }
    return json.dumps(http_data)


# In[]:



def getPredictedSeries(result):
    import random
    json_result = json.loads(result)
    y_data      = json_result['predictions'][0]
    y_mean      = y_data['mean']
    y_q1        = y_data['quantiles'][q1]
    y_q2        = y_data['quantiles'][q2]
    y_sample    = y_data['samples'][random.randint(0, num_samples)]
    return y_mean, y_q1, y_q2, y_sample


# In[]:

def plotSeries(result, truth=False, truth_data=None, truth_label=None):
    x = range(0,prediction_length)
    y_mean, y_q1, y_q2, y_sample = getPredictedSeries(result)
    plt.gcf().clear()
    predict_label,   = plt.plot(x, y_mean, label='predict')
    q1_label,     = plt.plot(x, y_q1, label=q1)
    q2_label,     = plt.plot(x, y_q2, label=q2)
    #sample_label, = plt.plot(x, y_sample, label='sample')

    if truth:
        ground_truth, = plt.plot(x, truth_data, label=truth_label)
        plt.legend(handles=[ground_truth, q2_label, predict_label, q1_label])
    else:
        plt.legend(handles=[q2_label, predict_label, q1_label])
    plt.yticks()
    plt.show()


# In[]:


year = 2018 # “He who controls the past controls the future."
prediction_data = buildPredictionData(year, trainingSet)
result = predictor.predict(prediction_data)
print(prediction_data)

plotSeries(result, 
           truth=True, 
           truth_data=trainingSet[str(year)][-prediction_length:], 
           truth_label='truth')
# In[]:
year = 2019
year_sealevel={}
year_sealevel[str(year)] = np.random.normal(90, 1.0, 7).tolist()
prediction_data = buildPredictionData(year, year_sealevel)
result = predictor.predict(prediction_data)
print(prediction_data)
plotSeries(result,
           truth=True, 
           truth_data=year_sealevel[str(year)][-prediction_length:], 
           truth_label='truth')
# In[ ]:
# In[ ]:
# In[ ]:



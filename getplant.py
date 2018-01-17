#!/usr/bin/python
import sys
sys.path.append('/home/grevius/.local/lib64/python3.4/site-packages/')

from miplant import MiPlant
from math import floor
from requests.auth import HTTPBasicAuth
import requests, time, json


UNITS = {"address": "", "firmware": "", "temperature": "°C",
         "light": "lux", "moisture": "%", "conductivity": "µS/cm",
         "battery": "%"}

OK_VALUES = {"address": "c4:7c:8d:62:74:3b",
             "firmware": "'3.1.8",
             "temperature": [18,25],
             "light": [2500, 50000],
             "moisture": [13, 50],
             "conductivity": [350, 1000],
             "battery": [10, 100]}

WARN_VALUES = {"address": "c4:7c:8d:62:74:3b", 
               "firmware": "'3.1.8",
               "temperature": [15, 30],
               "light": [1000, 70000],
               "moisture": [8, 60],
               "conductivity": [100, 1300],
               "battery": [3, 120]}

plantStates = {"address": 3, "firmware": 3, "temperature": 3,
               "light": 3, "moisture": 3, "conductivity": 3,
               "battery": 3}

ICINGA_STATE = ["OK","WARNING","CRITICAL","UNKNOWN"]


def getPlantValues():
    for plant in MiPlant.discover():
        return {"address": plant.address, "firmware": plant.firmware,
                "temperature": plant.temperature, "light": plant.light,
                "moisture": plant.moisture, "conductivity": plant.conductivity,
                "battery": plant.battery}
    return None

def pushValues(values):
    if values == None:
        return 3
    highestState = 0
    for key in values:
        if key in "temperature": # round temperature to be able to check if it is in range
            temperature, values[key] = values[key], floor(values[key])
        # print(key, values[key], UNITS[key])
        # checks if unit is not empty string (e.g. address and firmware)

        
        if between(values[key], WARN_VALUES[key]):
            #print(key,values[key],'is in warn')
            if between(values[key], OK_VALUES[key]):
                #print(key,values[key],'is in ok')
                temp = 0
            else:
                temp = 1
        else:
            #print(key,values[key],'is in critical')
            temp = 2
       
        plantStates[key] = temp
        if highestState < temp:
            highestState = temp
        if key in "temperature": # reset the temperature with the original, unfloored one
            values[key] = temperature
    return highestState, values

def between(value, r):
    #print(value,r)
    if isinstance(value,str):
        return value == r
    return r[0] <= value <= r[1]

def getPerformanceData(values):
    # 'label'=value[UOM];[warn];[crit];[min];[max]
    if values == None:
        return None
    performance_data = []
    values.pop("address")
    values.pop("firmware")
    for key in values:
        performance_data.append(("{}={};{}:{};{}:{};;".format(key,values[key],OK_VALUES[key][0],OK_VALUES[key][1],WARN_VALUES[key][0],WARN_VALUES[key][1])))
    #print(performance_data)
    return performance_data
    

timestamp = int(time.time())

highestState, values = pushValues(getPlantValues())
#print(plantStates)



payload = {"exit_status": highestState, 
           "plugin_output": "Plant is " + ICINGA_STATE[highestState], 
           "performance_data": getPerformanceData(values)}
#print(payload)
print(json.dumps(payload))



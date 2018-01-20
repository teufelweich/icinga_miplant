#!/usr/bin/python3
import json
from math import floor
import argparse

import requests
from requests.auth import HTTPBasicAuth

from miplant import MiPlant

parser = argparse.ArgumentParser(description="Fetch sensor values from Xiaomi FlowerCare over BLE, evaluate them "
                                             "and hand it to the nagios/icinga defined by URL")
parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
parser.add_argument("username", help="icinga api username")
parser.add_argument("password", help="icinga api password")
parser.add_argument("cert", help="icinga api certificate path")
args = parser.parse_args()

UNITS = {"address": "", "firmware": "", "temperature": "°C",
         "light": "lux", "moisture": "%", "conductivity": "µS/cm",
         "battery": "%"}

OK_VALUES = {"address": "c4:7c:8d:62:74:3b",
             "firmware": "'3.1.8",
             "temperature": [18, 25],
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

plant_states = {"address": 3, "firmware": 3, "temperature": 3,
                "light": 3, "moisture": 3, "conductivity": 3,
                "battery": 3}

ICINGA_STATE = ["OK", "WARNING", "CRITICAL", "UNKNOWN"]


def get_plant_values():  # connect to plant sensor and retrieve values
    if args.verbose:
        print("Try getting plant stats")
    for plant in MiPlant.discover():
        return {"address": plant.address, "firmware": plant.firmware,
                "temperature": plant.temperature, "light": plant.light,
                "moisture": plant.moisture, "conductivity": plant.conductivity,
                "battery": plant.battery}
    return None


def process_values(values):  # evaluates values based on given ranges
    if values is None:
        return 3
    highest_state = 0
    for key in values:
        if key in "temperature":  # round temperature to be able to check if it is in range
            temperature, values[key] = values[key], floor(values[key])

        # checks if unit is not empty string (e.g. address and firmware)

        if between(values[key], WARN_VALUES[key]):
            if args.verbose:
                print(key, values[key], 'is in warn')
            if between(values[key], OK_VALUES[key]):
                if args.verbose:
                    print(key, values[key], 'is in ok')
                temp = 0
            else:
                temp = 1
        else:
            if args.verbose:
                print(key, values[key], 'is in critical')
            temp = 2

        plant_states[key] = temp
        if highest_state < temp:
            highest_state = temp
        if key in "temperature":  # reset the temperature with the original, unfloored one
            values[key] = temperature
    return highest_state, values


def between(value, r):  # checks if value is in range r
    if isinstance(value, str):  # if value is string
        return value == r
    return r[0] <= value <= r[1]


def get_performance_data(values):  # translates values to performance data for nagios
    # from server expected syntax: 'label'=value[UOM];[warn];[crit];[min];[max]
    if values is None:
        return None
    performance_data = []
    values.pop("address")
    values.pop("firmware")
    for key in values:
        performance_data.append(("{}={};{}:{};{}:{};;".format(key, values[key], OK_VALUES[key][0], OK_VALUES[key][1],
                                                              WARN_VALUES[key][0], WARN_VALUES[key][1])))
    if args.verbose:
        print("Performance data:", performance_data)
    return performance_data


highest_state, processed_values = process_values(get_plant_values())
if highest_state == 3:  # try again, get_plant_values didn't retrieved anything
    if args.verbose:
        print("Fetching plant didn't work. Trying again")
    highest_state, processed_values = process_values(get_plant_values())

if args.verbose:
    print("Plant states:", plant_states)

payload = {"exit_status": highest_state,
           "plugin_output": "Plant is " + ICINGA_STATE[highest_state],
           "performance_data": get_performance_data(processed_values)}

if args.verbose:
    print("Payload:", json.dumps(payload))

                  auth=HTTPBasicAuth(args.username, args.password),
                  verify=args.cert, headers={"Accept": "application/json"})

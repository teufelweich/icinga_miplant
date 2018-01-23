#!/usr/bin/python3
import json
from math import floor
import argparse

import requests
import sys
from requests.auth import HTTPBasicAuth

from miplant import MiPlant

parser = argparse.ArgumentParser(description="Fetch sensor values from Xiaomi FlowerCare over BLE, evaluate them "
                                             "and hand it to the nagios/icinga defined by URL.")

parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
parser.add_argument("username", help="icinga api username")
parser.add_argument("password", help="icinga api password")
parser.add_argument("url", help="icinga api url")
parser.add_argument("cert", help="icinga api certificate path")

parser.add_argument("-a", help="ok value for mac address")
parser.add_argument("-f", help="ok value for firmware version")
parser.add_argument("-otu", help="upper ok value for temperature", default=25, type=int)
parser.add_argument("-otl", help="lower ok value for temperature", default=18, type=int)
parser.add_argument("-olu", help="upper ok value for light", default=50000, type=int)
parser.add_argument("-oll", help="lower ok value for light", default=1000, type=int)
parser.add_argument("-omu", help="upper ok value for moisture", default=50, type=int)
parser.add_argument("-oml", help="lower ok value for moisture", default=13, type=int)
parser.add_argument("-ocu", help="upper ok value for conductivity", default=1000, type=int)
parser.add_argument("-ocl", help="lower ok value for conductivity", default=350, type=int)
parser.add_argument("-obu", help="upper ok value for battery", default=100, type=int)
parser.add_argument("-obl", help="lower ok value for battery", default=10, type=int)

parser.add_argument("-wtu", help="upper warn value for temperature", default=30, type=int)
parser.add_argument("-wtl", help="lower warn value for temperature", default=15, type=int)
parser.add_argument("-wlu", help="upper warn value for light", default=70000, type=int)
parser.add_argument("-wll", help="lower warn value for light", default=500, type=int)
parser.add_argument("-wmu", help="upper warn value for moisture", default=60, type=int)
parser.add_argument("-wml", help="lower warn value for moisture", default=8, type=int)
parser.add_argument("-wcu", help="upper warn value for conductivity", default=1300, type=int)
parser.add_argument("-wcl", help="lower warn value for conductivity", default=100, type=int)
parser.add_argument("-wbu", help="upper warn value for battery", default=120, type=int)
parser.add_argument("-wbl", help="lower warn value for battery", default=3, type=int)

args = parser.parse_args()

UNITS = {"address": "", "firmware": "", "temperature": "°C",
         "light": "lux", "moisture": "%", "conductivity": "µS/cm",
         "battery": "%"}

OK_VALUES = {"address": args.a,
             "firmware": args.f,
             "temperature": [args.otl, args.otu],
             "light": [args.oll, args.olu],
             "moisture": [args.oml, args.omu],
             "conductivity": [args.ocl, args.ocu],
             "battery": [args.obl, args.obu]}

WARN_VALUES = {"address": OK_VALUES["address"],
               "firmware": OK_VALUES["firmware"],
               "temperature": [args.wtl, args.wtu],
               "light": [args.wll, args.wlu],
               "moisture": [args.wml, args.wmu],
               "conductivity": [args.wcl, args.wcu],
               "battery": [args.wbl, args.wbu]}

plant_states = {"address": 3, "firmware": 3, "temperature": 3,
                "light": 3, "moisture": 3, "conductivity": 3,
                "battery": 3}

ICINGA_STATE = ["OK", "WARNING", "CRITICAL", "UNKNOWN"]


#  maybe create type to pass args like "-t 15,25;10,30"
# def range_list(string):
#    values = [int(i) for i in string.split(";")]
#    print(values)
#


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
        if between(values[key], WARN_VALUES[key]):
            if between(values[key], OK_VALUES[key]):
                temp = 0
            else:
                temp = 1
        else:
            temp = 2

        if args.verbose:
            print(key, values[key], 'is', ICINGA_STATE[temp])

        plant_states[key] = temp
        if highest_state < temp:  # new highest state
            highest_state = temp
    return highest_state, values


def between(value, r):  # checks if value is in range r
    if isinstance(value, str):  # if value is string
        return value == r
    return r[0] <= floor(value) <= r[1]


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
    return performance_data


highest_state, processed_values = process_values(get_plant_values())
if highest_state == 3:  # try again, get_plant_values didn't retrieved anything
    if args.verbose:
        print("Fetching plant didn't work. Trying again")
    highest_state, processed_values = process_values(get_plant_values())

payload = {"exit_status": highest_state,
           "plugin_output": "Plant is " + ICINGA_STATE[highest_state],
           "performance_data": get_performance_data(processed_values)}

if args.verbose:
    print("Payload:", json.dumps(payload, sort_keys=True, indent=4))

for tries in range(0, 2):
    try:
        r = requests.post(args.url, data=json.dumps(payload), auth=HTTPBasicAuth(args.username, args.password),
                          verify=args.cert, headers={"Accept": "application/json"})
        r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(err)
        sys.exit(1)
    except requests.exceptions.Timeout as err_t:
        if tries > 2:
            print(err_t)
            print("Connection timed out too often, exiting")
            sys.exit(1)
        print("Connection timed out... trying again")
    except requests.exceptions.RequestException as e:
        # catastrophic error
        print(e)
        sys.exit(1)

if args.verbose:
    print(json.loads(r.text))
    print(r.reason)

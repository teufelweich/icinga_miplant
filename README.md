# check_miplant.py
This script uses the [MiPlant](https://github.com/kipe/miplant) library
to fetch the sensor values from a Xiaomi FlowerCare device over
bluetooth LE. These values then get evaluated based on the given or
default (suitable for *ficus benjamina exotica*) value ranges and then
send to your icinga/nagios api.

## Usage
```
./getplant.py api_username api_password api_url api_cert -a "b2:3f:8d:5e:73:d7" -f "'3.1.8"
```


## Limitations
- because MiPlant uses `gattlib` this script must be run as root
- only one FlowerCare device can be processed with this script at a time
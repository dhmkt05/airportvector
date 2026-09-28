# Copyright (c) 2026 AirportVector Authors
# This source code is licensed under the Business Source License 1.1 (BSL).
# Free for development, non-commercial use, and internal deployment.
# Commercial SaaS hosting or paid API distribution is strictly prohibited.
# See LICENSE.md in the root directory for full terms.

import math

AIRPORT_REGISTRY = {
    "TRZ": {"lat": 10.7651, "lon": 78.7097, "name": "Trichy"},
    "MAA": {"lat": 12.9941, "lon": 80.1709, "name": "Chennai"},
    "LAX": {"lat": 33.9416, "lon": -118.4085, "name": "Los Angeles"}
}

METERS_PER_LAT_DEGREE = 111000

def get_meters_per_lon_degree(latitude):
    return 111000 * math.cos(math.radians(latitude))

def encode(airport_code, target_lat, target_lon, precision_digits=6):
    if airport_code not in AIRPORT_REGISTRY:
        raise ValueError("Airport code not registered.")
    base = AIRPORT_REGISTRY[airport_code]
    delta_lat = target_lat - base["lat"]
    delta_lon = target_lon - base["lon"]
    y_meters = delta_lat * METERS_PER_LAT_DEGREE
    x_meters = delta_lon * get_meters_per_lon_degree(base["lat"])
    
    if x_meters >= 0 and y_meters >= 0:
        sector = "A"
    elif x_meters >= 0 and y_meters < 0:
        sector = "B"
    elif x_meters < 0 and y_meters < 0:
        sector = "C"
    else:
        sector = "D"
        
    abs_x = abs(x_meters)
    abs_y = abs(y_meters)
    digit_pool = precision_digits // 2
    scale_factor = 10 ** (3 - digit_pool)
    scaled_x = int(round(abs_x / scale_factor))
    scaled_y = int(round(abs_y / scale_factor))
    
    return f"{airport_code}-{sector}{str(scaled_x).zfill(digit_pool)}{str(scaled_y).zfill(digit_pool)}"

def decode(input_code):
    try:
        airport_code, payload = input_code.split("-")
    except ValueError:
        raise ValueError("Invalid format. Must include a hyphen.")
    if airport_code not in AIRPORT_REGISTRY:
        raise ValueError("Unknown airport anchor code.")
    base = AIRPORT_REGISTRY[airport_code]
    sector = payload[0].upper()
    numeric_string = payload[1:]
    precision_digits = len(numeric_string)
    digit_pool = precision_digits // 2
    
    str_x = numeric_string[:digit_pool]
    str_y = numeric_string[digit_pool:]
    scale_factor = 10 ** (3 - digit_pool)
    abs_x = int(str_x) * scale_factor
    abs_y = int(str_y) * scale_factor
    
    if sector == "A": x_meters, y_meters = abs_x, abs_y
    elif sector == "B": x_meters, y_meters = abs_x, -abs_y
    elif sector == "C": x_meters, y_meters = -abs_x, -abs_y
    elif sector == "D": x_meters, y_meters = -abs_x, abs_y
    else: raise ValueError("Invalid Sector Character.")
        
    target_lat = base["lat"] + (y_meters / METERS_PER_LAT_DEGREE)
    target_lon = base["lon"] + (x_meters / get_meters_per_lon_degree(base["lat"]))
    return round(target_lat, 6), round(target_lon, 6)

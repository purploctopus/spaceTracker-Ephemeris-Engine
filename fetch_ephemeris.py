#
#        f"https://ssd.jpl.nasa.gov/api/horizons.api?"
#        f"format=text&COMMAND='{planet_code}'&OBJ_DATA='NO'&MAKE_EPHEM='YES'&"
#        f"EPHEM_TYPE='OBSERVER'&CENTER='500@399'&START_TIME='{safe_start}'&"
#        f"STOP_TIME='{safe_stop}'&STEP_SIZE='1%20m'&QUANTITIES='1'"
#        f"https://ssd.jpl.nasa.gov/api/horizons.api?"
#        f"format=text&COMMAND='{planet_code}'&OBJ_DATA='NO'&MAKE_EPHEM='YES'&"
#        f"EPHEM_TYPE='OBSERVER'&CENTER='500@399'&START_TIME='{safe_start}'&"
#        f"STOP_TIME='{safe_stop}'&STEP_SIZE='1%20m'&QUANTITIES='1,20'"

import os
import json
import urllib.request
import urllib.parse
import time
import calendar
from datetime import datetime, timedelta

PLANETS = {
    "MERCURY": "199",
    "VENUS": "299",
    "MARS": "499",
    "JUPITER": "599",
    "SATURN": "699"
}

def calculate_current_gmst():
    now = datetime.utcnow()
    time_tuple = now.timetuple()
    unix_seconds = calendar.timegm(time_tuple)
    d = (unix_seconds - 946728000) / 86400.0
    T = d / 36525.0
    gmst_degrees = 280.46061837 + 360.98564736629 * d + 0.000387933 * T * T - (T * T * T / 38710000.0)
    gmst_degrees = gmst_degrees % 360.0
    if gmst_degrees < 0: gmst_degrees += 360.0
    return round(gmst_degrees / 15.0, 6)

def fetch_planet_coords(planet_code):
    now = datetime.utcnow()
    start_str = now.strftime('%Y-%m-%d %H:%M')
    stop_str = (now + timedelta(minutes=2)).strftime('%Y-%m-%d %H:%M')
    
    safe_start = urllib.parse.quote(start_str)
    safe_stop = urllib.parse.quote(stop_str)
    
    # 💡 UPDATED QUANTITIES MATRIX:
    # Adding ',20' forces NASA to output the precise delta range distance columns (expressed in Astronomical Units)!
    url = (
        f"https://ssd.jpl.nasa.gov/api/horizons.api?"
        f"format=text&COMMAND='{planet_code}'&OBJ_DATA='NO'&MAKE_EPHEM='YES'&"
        f"EPHEM_TYPE='OBSERVER'&CENTER='500@399'&START_TIME='{safe_start}'&"
        f"STOP_TIME='{safe_stop}'&STEP_SIZE='1%20m'&QUANTITIES='1,20'"
    )
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'spaceTracker-Core'})
        with urllib.request.urlopen(req) as response:
            text = response.read().decode('utf-8')
            
            soe = text.find("$$SOE")
            eoe = text.find("$$EOE")
            if soe == -1 or eoe == -1: return None
            
            data_block = text[soe+5:eoe].strip()
            lines = [l for l in data_block.split('\n') if l.strip()]
            if not lines: return None
            
            target_line = lines[0]
            
            # Slice character layout slots directly matching NASA's fixed spacing grid
            ra_text = target_line[22:34].strip().split()
            dec_text = target_line[34:46].strip().split()
            
            # Column 47-66 holds the high-precision delta distance field
            distance_text = target_line[46:66].strip()
            
            if len(ra_text) < 3 or len(dec_text) < 3: return None
            
            ra_hours = float(ra_text[0]) + (float(ra_text[1]) / 60.0) + (float(ra_text[2]) / 3600.0)
            
            dec_deg = float(dec_text[0])
            dec_min = float(dec_text[1])
            dec_sec = float(dec_text[2])
            is_negative = dec_text[0].startswith('-')
            decimal_dec = abs(dec_deg) + (dec_min / 60.0) + (dec_sec / 3600.0)
            if is_negative: decimal_dec *= -1.0
            
            # Extract the raw range value float
            true_distance_au = float(distance_text)
            
            return round(ra_hours, 4), round(decimal_dec, 4), round(true_distance_au, 6)
            
    except Exception as e:
        print(f"❌ Error parsing planet code {planet_code}: {e}")
        return None

def main():
    planet_list = []
    current_gmst = calculate_current_gmst()
    
    for name, code in PLANETS.items():
        coords = fetch_planet_coords(code)
        if coords:
            planet_list.append({
                "name": name,
                "ra": coords[0],
                "dec": coords[1],
                "range_au": coords[2] # Lock the true distance directly into the data contract packet
            })
            print(f"✅ Extracted {name}: RA {coords[0]}h, DEC {coords[1]}°, DIST {coords[2]} AU")
            
    if planet_list:
        integrated_payload = {
            "gmst_hours": current_gmst,
            "planets": planet_list
        }
        
        with open("ephemeris.json", "w") as file:
            json.dump(integrated_payload, file, indent=2)
        print(f"🚀 Master Payload Unified Successfully. GMST: {current_gmst}h")

if __name__ == "__main__":
    main()


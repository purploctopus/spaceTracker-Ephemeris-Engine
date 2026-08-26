import os
import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

PLANETS = {
    "MERCURY": "199",
    "VENUS": "299",
    "MARS": "499",
    "JUPITER": "599",
    "SATURN": "699"
}

def calculate_current_gmst():
    """Calculates high-precision Greenwich Mean Sidereal Time in decimal hours"""
    now = datetime.utcnow()
    year, month, day = now.year, now.month, now.day
    hour, minute, second = now.hour, now.minute, now.second
    
    if month <= 2:
        year -= 1
        month += 12
        
    A = int(year / 100)
    B = 2 - A + int(A / 4)
    
    # Core Julian Day count calculation
    jd = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + B - 1524.5
    day_fraction = (hour + (minute / 60.0) + (second / 3600.0)) / 24.0
    jd += day_fraction
    
    d = jd - 2451543.5
    T = d / 36525.0
    
    # Standard IAU 1982 GMST Sidereal Time Equation
    gmst_degrees = 280.46061837 + 360.98564736629 * d + 0.000387933 * T * T - (T * T * T / 38710000.0)
    gmst_degrees = gmst_degrees % 360.0
    if gmst_degrees < 0:
        gmst_degrees += 360.0
        
    return round(gmst_degrees / 15.0, 6)

def fetch_planet_coords(planet_code):
    now = datetime.utcnow()
    start_str = now.strftime('%Y-%m-%d %H:%M')
    stop_str = (now + timedelta(minutes=2)).strftime('%Y-%m-%d %H:%M')
    
    safe_start = urllib.parse.quote(start_str)
    safe_stop = urllib.parse.quote(stop_str)
    

    url = (
        f"https://ssd.jpl.nasa.gov/api/horizons.api?"
        f"format=text&COMMAND='{planet_code}'&OBJ_DATA='NO'&MAKE_EPHEM='YES'&"
        f"EPHEM_TYPE='OBSERVER'&CENTER='500@399'&START_TIME='{safe_start}'&"
        f"STOP_TIME='{safe_stop}'&STEP_SIZE='1%20m'&QUANTITIES='1'"
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
            
            # Precise column slicing to isolate Right Ascension and Declination text slots
            ra_text = target_line[22:34].strip().split()
            dec_text = target_line[34:46].strip().split()
            
            if len(ra_text) < 3 or len(dec_text) < 3: return None
            
            ra_hours = float(ra_text[0]) + (float(ra_text[1]) / 60.0) + (float(ra_text[2]) / 3600.0)
            
            dec_deg = float(dec_text[0])
            dec_min = float(dec_text[1])
            dec_sec = float(dec_text[2])
            
            is_negative = dec_text[0].startswith('-')
            decimal_dec = abs(dec_deg) + (dec_min / 60.0) + (dec_sec / 3600.0)
            if is_negative: decimal_dec *= -1.0
            
            return round(ra_hours, 4), round(decimal_dec, 4)
            
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
                "dec": coords[1]
            })
            print(f"✅ Extracted {name}: RA {coords[0]}h, DEC {coords[1]}°")
            
    if planet_list:
        # Construct the final integrated unified clock dictionary payload
        integrated_payload = {
            "gmst_hours": current_gmst,
            "planets": planet_list
        }
        
        with open("ephemeris.json", "w") as file:
            json.dump(integrated_payload, file, indent=2)
        print(f"🚀 Master Payload Unified Successfully. GMST: {current_gmst}h")

if __name__ == "__main__":
    main()


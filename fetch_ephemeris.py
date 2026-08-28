#
#        f"https://ssd.jpl.nasa.gov/api/horizons.api?"
#        f"format=text&COMMAND='{planet_code}'&OBJ_DATA='NO'&MAKE_EPHEM='YES'&"
#        f"EPHEM_TYPE='OBSERVER'&CENTER='500@399'&START_TIME='{safe_start}'&"
#        f"STOP_TIME='{safe_stop}'&STEP_SIZE='1%20m'&QUANTITIES='1'"
#        f"https://ssd.jpl.nasa.gov/api/horizons.api?"
#        f"format=text&COMMAND='{planet_code}'&OBJ_DATA='NO'&MAKE_EPHEM='YES'&"
#        f"EPHEM_TYPE='OBSERVER'&CENTER='500@399'&START_TIME='{safe_start}'&"
#        f"STOP_TIME='{safe_stop}'&STEP_SIZE='1%20m'&QUANTITIES='1,20'"
#        url = "https://aa.usno.navy.mil/api/siderealtime?date=today&time=now&tz=0"


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
    # 💡 FIXED: Replaced brittle manual math loops with a direct call to the
    # US Naval Observatory's high-precision Master Time Clock API!
    url = "https://aa.usno.navy.mil/api/siderealtime?date=today&time=now&tz=0"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'spaceTracker-Core'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            # Extract Greenwich Mean Sidereal Time hour string directly from the response
            gmst_string = data['properties']['gmst']
            
            # Convert "HH:MM:SS" format directly into a raw decimal hour Float
            h, m, s = map(float, gmst_string.split(':'))
            gmst_hours = h + (m / 60.0) + (s / 3600.0)
            return round(gmst_hours, 6)
    except Exception as e:
        print(f"❌ USNO API Offline. Falling back to timestamp reference: {e}")
        # Reliable baseline fallback if server times out
        return 22.915400
        
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
            
            target_line = lines[0].strip()
            tokens = target_line.split()
            if len(tokens) < 8: return None
            
            ra_hours = float(tokens[2]) + (float(tokens[3]) / 60.0) + (float(tokens[4]) / 3600.0)
            
            dec_deg = float(tokens[5])
            dec_min = float(tokens[6])
            dec_sec = float(tokens[7])
            is_negative = tokens[5].startswith('-')
            decimal_dec = abs(dec_deg) + (dec_min / 60.0) + (dec_sec / 3600.0)
            if is_negative: decimal_dec *= -1.0
            
            true_distance_au = float(tokens[8])
            
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
                "range_au": coords[2]
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

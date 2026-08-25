import os
import json
import urllib.request
import re
from datetime import datetime, timedelta

# NASA JPL Horizons object codes for the five major planets
PLANETS = {
    "MERCURY": "199",
    "VENUS": "299",
    "MARS": "499",
    "JUPITER": "599",
    "SATURN": "699"
}

def fetch_planet_coords(planet_code):
    # Set time boundaries for a narrow 5-minute data window
    now = datetime.utcnow()
    start_str = now.strftime('%Y-%m-%d %H:%M')
    stop_str = (now + timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M')
    
    # 🔗 Official NASA JPL Horizons Query URL (Geocentric System Center 500@399)
    url = (
        f"https://nasa.gov?"
        f"format=text&COMMAND='{planet_code}'&OBJ_DATA='NO'&MAKE_EPHEM='YES'&"
        f"EPHEM_TYPE='OBSERVER'&CENTER='500@399'&START_TIME='{start_str}'&"
        f"STOP_TIME='{stop_str}'&STEP_SIZE='1%20m'&QUANTITIES='1'"
    )
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'spaceTracker-App'})
        with urllib.request.urlopen(req) as response:
            text = response.read().decode('utf-8')
            
            # Locate NASA's absolute Ephemeris text data boundaries
            soe_marker = text.find("$$SOE")
            eoe_marker = text.find("$$EOE")
            if soe_marker == -1 or eoe_marker == -1:
                print(f"❌ Marker boundary missing for planet code {planet_code}")
                return None
            
            # Isolate the data rows sitting between the markers
            raw_data_block = text[soe_marker+5:eoe_marker].strip()
            lines = raw_data_block.split('\n')
            if not lines or len(lines[0].strip()) == 0:
                print(f"❌ Empty data block chunk for planet code {planet_code}")
                return None
                
            # Take the very first time row in the window matrix
            target_line = lines[0].strip()
            
            # Use regex to strip away the date stamps and extract clean coordinate values
            # NASA format: Date__Time (UTC)  R.A.___(apparent)___DEC
            # Example: 2026-Aug-25 18:45  11 24 32.12 +04 12 15.3
            match = re.search(r'\d{4}-\w{3}-\d{2}\s+\d{2}:\d{2}\s+(\d{2})\s+(\d{2})\s+(\d+.\d+)\s+([+-]?\d{2})\s+(\d{2})\s+(\d+.\d+)', target_line)
            
            if not match:
                print(f"❌ Regex extraction failed on data row line: '{target_line}'")
                return None
                
            # Extract Right Ascension tokens -> Convert directly to uniform decimal hours
            ra_h = float(match.group(1))
            ra_m = float(match.group(2))
            ra_s = float(match.group(3))
            decimal_ra = ra_h + (ra_m / 60.0) + (ra_s / 3600.0)
            
            # Extract Declination tokens -> Convert directly to uniform decimal degrees
            dec_d = float(match.group(4))
            dec_m = float(match.group(5))
            dec_s = float(match.group(6))
            
            # Preserve negative signs cleanly across the mathematical inversion
            is_negative = match.group(4).startswith('-')
            abs_deg = abs(dec_d)
            decimal_dec = abs_deg + (dec_m / 60.0) + (dec_s / 3600.0)
            if is_negative: decimal_dec *= -1.0
            
            return round(decimal_ra, 4), round(decimal_dec, 4)
            
    except Exception as e:
        print(f"❌ Critical runtime parse fail on planet code {planet_code}: {e}")
        return None

def main():
    output_catalog = []
    
    for name, code in PLANETS.items():
        coords = fetch_planet_coords(code)
        if coords:
            output_catalog.append({
                "name": name,
                "ra": coords[0],
                "dec": coords[1]
            })
            print(f"✅ Successfully Extracted {name}: RA {coords[0]}h, DEC {coords[1]}°")
            
    if output_catalog:
        with open("ephemeris.json", "w") as file:
            json.dump(output_catalog, file, indent=2)
        print("🚀 Ephemeris pipeline generation sweep completed successfully.")
    else:
        print("❌ CRITICAL: No data parsed. Terminating to protect existing database file.")

if __name__ == "__main__":
    main()


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

def fetch_planet_coords(planet_code):
    now = datetime.utcnow()
    start_str = now.strftime('%Y-%m-%d %H:%M')
    stop_str = (now + timedelta(minutes=2)).strftime('%Y-%m-%d %H:%M')
    
    safe_start = urllib.parse.quote(start_str)
    safe_stop = urllib.parse.quote(stop_str)
    
    # 💡 THE RAW SCIENCE LINK HOOK:
    # Querying quantity mode '1' tells NASA to return the absolute, live Apparent
    # Right Ascension and Declination columns corrected for today's real-time wobble!

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
            
            # Extract the raw data row text lines sitting between the markers
            data_block = text[soe+5:eoe].strip()
            lines = [l for l in data_block.split('\n') if l.strip()]
            if not lines: return None
            
            # Take the active live timestamp data row line
            target_line = lines[0]
            
            # 💡 FIXED COLUMN SLICING SCHEMA:
            # NASA observer tables use strict fixed-width character spaces.
            # We bypass regular expression guessing and slice the exact character slots!
            # Columns 23-34: Right Ascension (HH MM SS.SS)
            # Columns 35-46: Declination (sDD MM SS.S)
            ra_text = target_line[22:34].strip().split()
            dec_text = target_line[34:46].strip().split()
            
            if len(ra_text) < 3 or len(dec_text) < 3: return None
            
            # Convert RA segments cleanly to decimal hours
            ra_hours = float(ra_text[0]) + (float(ra_text[1]) / 60.0) + (float(ra_text[2]) / 3600.0)
            
            # Convert Dec segments cleanly to decimal degrees, keeping signs intact
            dec_deg = float(dec_text[0])
            dec_min = float(dec_text[1])
            dec_sec = float(dec_text[2])
            
            is_negative = dec_text[0].startswith('-')
            decimal_dec = abs(dec_deg) + (dec_min / 60.0) + (dec_sec / 3600.0)
            if is_negative: decimal_dec *= -1.0
            
            return round(ra_hours, 4), round(decimal_dec, 4)
            
    except Exception as e:
        print(f"❌ Error scraping planet code {planet_code}: {e}")
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
            print(f"✅ Extracted {name}: RA {coords[0]}h, DEC {coords[1]}°")
            
    if output_catalog:
        with open("ephemeris.json", "w") as file:
            json.dump(output_catalog, file, indent=2)
        print("🚀 Ephemeris generation finalized successfully.")

if __name__ == "__main__":
    main()

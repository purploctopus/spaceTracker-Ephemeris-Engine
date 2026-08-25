import os
import json
import urllib.request
from datetime import datetime

# NASA JPL Horizons object codes for the five major planets
PLANETS = {
    "MERCURY": "199",
    "VENUS": "299",
    "MARS": "499",
    "JUPITER": "599",
    "SATURN": "699"
}

def fetch_planet_coords(planet_code):
    now_str = datetime.utcnow().strftime('%Y-%m-%d')
    
    # URL parameter center '500@399' requests Geocentric positions (Center of the Earth)
    url = (
        f"https://nasa.gov?"
        f"format=text&COMMAND='{planet_code}'&OBJ_DATA='NO'&MAKE_EPHEM='YES'&"
        f"EPHEM_TYPE='OBSERVER'&CENTER='500@399'&START_TIME='{now_str}'&"
        f"STOP_TIME='{now_str}%2000:05'&STEP_SIZE='1%20d'&QUANTITIES='1'"
    )
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            text = response.read().decode('utf-8')
            
            soe = text.find("$$SOE")
            eoe = text.find("$$EOE")
            if soe == -1 or eoe == -1: return None
            
            data_line = text[soe+5:eoe].strip().split('\n')[0]
            tokens = data_line.split()
            
            if len(tokens) < 8: return None
            
            # Convert Right Ascension (Hours, Minutes, Seconds) to clean decimal hours
            ra_hours = float(tokens[2]) + float(tokens[3])/60.0 + float(tokens[4])/3600.0
            
            # Convert Declination (Degrees, Minutes, Seconds) to clean decimal degrees
            dec_sign = -1.0 if tokens[5].startswith('-') else 1.0
            dec_deg_str = tokens[5].replace('-', '').replace('+', '')
            dec_degrees = (float(dec_deg_str) + float(tokens[6])/60.0 + float(tokens[7])/3600.0) * dec_sign
            
            return round(ra_hours, 4), round(dec_degrees, 4)
    except Exception as e:
        print(f"❌ Aborting node parse safely on planet code {planet_code}: {e}")
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
        print("🚀 Ephemeris local file written cleanly.")

if __name__ == "__main__":
    main()


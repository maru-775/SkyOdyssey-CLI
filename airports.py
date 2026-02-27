# Major airports by region for exploratory search

AIRPORTS_BY_REGION = {
    "Europe": [
        # Major Hubs & Western Europe
        "CDG", "ORY", "NCE", "LYS", "MRS", "TLS", "BOD", "NTE", # France
        "LHR", "LGW", "STN", "LTN", "MAN", "EDI", "GLA", "BHX", "BRS", # UK
        "DUB", "ORK", "SNN", "NOC", # Ireland
        "FRA", "MUC", "BER", "DUS", "HAM", "STR", "CGN", "LEJ", "HAJ", "NUE", # Germany
        "AMS", "EIN", "BRU", "CRL", # Benelux
        "MAD", "BCN", "PMI", "AGP", "VLC", "SVQ", "LIS", "OPO", "FAO", # Spain & Portugal
        "FCO", "MXP", "VCE", "BGY", "NAP", "PSA", "BLQ", # Italy
        "ZRH", "GVA", "VIE", "CPH", "OSL", "ARN", "HEL", "KEF", # Central & Nordic
        # Eastern Europe & Balkans
        "WAW", "KRK", "GDN", "PRG", "BUD", "OTP", "SOF", "BEG", "SKP", "TIA", 
        "RIX", "VNO", "TLL", "MSQ", "KBP", # Note: MSQ/KBP included for completeness, may lack flights
        "ATH", "SKG", "HER", "IST", "SAW" # Southeast
    ],
    "North America": [
        "ATL", "LAX", "ORD", "DFW", "DEN", "JFK", "SFO", "SEA", "LAS", "MCO",
        "EWR", "CLT", "PHX", "IAH", "MIA", "YYZ", "YVR", "MEX", "BOS", "IAD"
    ],
    "Asia": [
        "HND", "ICN", "SIN", "HKG", "BKK", "PVG", "PEK", "NRT", "TPE", "KUL",
        "DEL", "BOM", "DXB", "DOH", "AUH", "SGN", "HAN", "MNL", "CGK"
    ],
    "Oceania": [
        "SYD", "MEL", "BNE", "PER", "AKL", "CHC"
    ],
    "South America": [
        "GRU", "BOG", "SCL", "LIM", "EZE", "GIG"
    ],
    "Africa": [
        "JNB", "CPT", "CAI", "CAS", "NBO", "ADD"
    ]
}

# Mapping of airports to countries for exclusion logic
AIRPORT_TO_COUNTRY = {
    # France
    "CDG": "France", "ORY": "France", "NCE": "France", "LYS": "France", "MRS": "France", "TLS": "France", "BOD": "France", "NTE": "France",
    # UK
    "LHR": "UK", "LGW": "UK", "STN": "UK", "LTN": "UK", "MAN": "UK", "EDI": "UK", "GLA": "UK", "BHX": "UK", "BRS": "UK",
    # Ireland
    "DUB": "Ireland", "ORK": "Ireland", "SNN": "Ireland", "NOC": "Ireland",
    # Germany
    "FRA": "Germany", "MUC": "Germany", "BER": "Germany", "DUS": "Germany", "HAM": "Germany", "STR": "Germany", "CGN": "Germany", "LEJ": "Germany", "HAJ": "Germany", "NUE": "Germany",
    # Benelux
    "AMS": "Netherlands", "EIN": "Netherlands", "BRU": "Belgium", "CRL": "Belgium",
    # Spain & Portugal
    "MAD": "Spain", "BCN": "Spain", "PMI": "Spain", "AGP": "Spain", "VLC": "Spain", "SVQ": "Spain", "LIS": "Portugal", "OPO": "Portugal", "FAO": "Portugal",
    # Italy
    "FCO": "Italy", "MXP": "Italy", "VCE": "Italy", "BGY": "Italy", "NAP": "Italy", "PSA": "Italy", "BLQ": "Italy",
    # Central & Nordic
    "ZRH": "Switzerland", "GVA": "Switzerland", "VIE": "Austria", "CPH": "Denmark", "OSL": "Norway", "ARN": "Sweden", "HEL": "Finland", "KEF": "Iceland",
    # Eastern Europe & Balkans
    "WAW": "Poland", "KRK": "Poland", "GDN": "Poland", "PRG": "Czechia", "BUD": "Hungary", "OTP": "Romania", "SOF": "Bulgaria", "BEG": "Serbia", "SKP": "North Macedonia", "TIA": "Albania", 
    "RIX": "Latvia", "VNO": "Lithuania", "TLL": "Estonia", "MSQ": "Belarus", "KBP": "Ukraine",
    # Southeast
    "ATH": "Greece", "SKG": "Greece", "HER": "Greece", "IST": "Turkey", "SAW": "Turkey"
}

# Hub groups for airport change detection
CITY_HUBS = {
    "Paris": ["CDG", "ORY", "BVA"],
    "London": ["LHR", "LGW", "STN", "LTN", "LCY", "SEN"],
    "Milan": ["MXP", "LIN", "BGY"],
    "Rome": ["FCO", "CIA"],
    "Berlin": ["BER"],
    "Madrid": ["MAD"],
    "Barcelona": ["BCN"],
    "Istanbul": ["IST", "SAW"],
    "New York": ["JFK", "EWR", "LGA"],
    "Tokyo": ["HND", "NRT"],
}

# Reverse mapping for quick lookup
AIRPORT_TO_HUB = {code: hub for hub, codes in CITY_HUBS.items() for code in codes}

def get_airports_for_region(region: str):
    if not region:
        region = "All"

    region_normalized = region.strip().lower()
    if region_normalized == "all":
        all_airports = []
        for airports in AIRPORTS_BY_REGION.values():
            all_airports.extend(airports)
        return all_airports

    for region_name, airports in AIRPORTS_BY_REGION.items():
        if region_name.lower() == region_normalized:
            return airports

    return []

def get_airports_excluding(region: str, excluded_countries: list = None, excluded_airports: list = None):
    """Returns airports in a region excluding specific countries or airport codes."""
    airports = get_airports_for_region(region)
    if not excluded_countries and not excluded_airports:
        return airports
    
    excluded_countries = [c.lower() for c in (excluded_countries or [])]
    excluded_airports = [a.upper() for a in (excluded_airports or [])]
    
    filtered = []
    for code in airports:
        if code in excluded_airports:
            continue
        country = AIRPORT_TO_COUNTRY.get(code)
        if country and country.lower() in excluded_countries:
            continue
        filtered.append(code)
    return filtered

def get_all_regions():
    return list(AIRPORTS_BY_REGION.keys())

def get_airport_hub(code: str):
    """Returns the city hub name for an airport code, if known."""
    return AIRPORT_TO_HUB.get(code.upper())

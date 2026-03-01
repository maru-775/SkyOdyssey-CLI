AIRPORTS_BY_REGION = {
    "Europe": [
        # France
        "CDG", "ORY", "NCE", "LYS", "MRS", "TLS", "BOD", "NTE", 
        # UK & Ireland
        "LHR", "LGW", "STN", "LTN", "MAN", "EDI", "GLA", "BHX", "BRS", "DUB", "ORK", "SNN", "NOC",
        # Germany
        "FRA", "MUC", "BER", "DUS", "HAM", "STR", "CGN", "LEJ", "HAJ", "NUE",
        # Benelux & Central
        "AMS", "EIN", "BRU", "CRL", "ZRH", "GVA", "VIE",
        # Spain & Portugal
        "MAD", "BCN", "PMI", "AGP", "VLC", "SVQ", "LIS", "OPO", "FAO",
        # Italy
        "FCO", "MXP", "VCE", "BGY", "NAP", "PSA", "BLQ",
        # Nordic & Baltic
        "CPH", "OSL", "ARN", "HEL", "KEF", "RIX", "VNO", "TLL",
        # Eastern Europe & Balkans
        "WAW", "KRK", "GDN", "PRG", "BUD", "OTP", "SOF", "BEG", "SKP", "TIA", "MSQ", "KBP",
        # Southeast
        "ATH", "SKG", "HER", "IST", "SAW"
    ],
    "North America": [
        "ATL", "LAX", "ORD", "DFW", "DEN", "JFK", "SFO", "SEA", "LAS", "MCO",
        "EWR", "CLT", "PHX", "IAH", "MIA", "BOS", "IAD", "DCA", "SAN", "TPA", 
        "PHL", "MSP", "DTW", "SLC", "FLL", "BWI", "MDW",
        "YYZ", "YVR", "YUL", "YYC", "YEG", "YOW", # Canada
        "MEX", "CUN", "GDL", "MTY" # Mexico
    ],
    "Asia": [
        "HND", "ICN", "SIN", "HKG", "BKK", "PVG", "PEK", "NRT", "TPE", "KUL",
        "DEL", "BOM", "DXB", "DOH", "AUH", "SGN", "HAN", "MNL", "CGK",
        "PKX", "CAN", "SZX", "CTU", "KMG", "SHA", # China
        "KIX", "CTS", "FUK", # Japan
        "BLR", "HYD", "MAA", "CCU", # India
        "RUH", "JED", "KWI", "MCT" # Middle East
    ],
    "Africa": [
        # North Africa & Morocco
        "CMN", "RAK", "AGA", "TNG", "FEZ", "RBA", "NDR", "OUD", # Morocco
        "CAI", "HRG", "SSH", "LXR", "ASW", "RMF", "HBE", "SPX", # Egypt
        "ALG", "ORA", "AAE", "CZL", # Algeria
        "TUN", "DJE", "MIR", "SFA", # Tunisia
        "TIP", "BEN", "MJI", # Libya
        # Sub-Saharan Africa
        "JNB", "CPT", "DUR", "HLA", "ADD", "NBO", "MBA", "LOS", "ABV", 
        "ACC", "DSS", "DKR", "ABJ", "DAR", "ZNZ", "EBB", "KGL", "HRE", "MPM", "LAD"
    ],
    "Oceania": [
        "SYD", "MEL", "BNE", "PER", "ADL", "OOL", "CNS", "AKL", "CHC", "WLG", "NAN"
    ],
    "South America": [
        "GRU", "BOG", "SCL", "LIM", "EZE", "GIG", "AEP", "VVI", "UIO", "ASU", "MVD", "MDE"
    ]
}

AIRPORT_TO_COUNTRY = {
    # Europe - France
    "CDG": "France", "ORY": "France", "NCE": "France", "LYS": "France", "MRS": "France", "TLS": "France", "BOD": "France", "NTE": "France",
    # UK
    "LHR": "UK", "LGW": "UK", "STN": "UK", "LTN": "UK", "MAN": "UK", "EDI": "UK", "GLA": "UK", "BHX": "UK", "BRS": "UK",
    # Ireland
    "DUB": "Ireland", "ORK": "Ireland", "SNN": "Ireland", "NOC": "Ireland",
    # Germany
    "FRA": "Germany", "MUC": "Germany", "BER": "Germany", "DUS": "Germany", "HAM": "Germany", "STR": "Germany", "CGN": "Germany", "LEJ": "Germany", "HAJ": "Germany", "NUE": "Germany",
    # Benelux & Central
    "AMS": "Netherlands", "EIN": "Netherlands", "BRU": "Belgium", "CRL": "Belgium", "ZRH": "Switzerland", "GVA": "Switzerland", "VIE": "Austria",
    # Spain & Portugal
    "MAD": "Spain", "BCN": "Spain", "PMI": "Spain", "AGP": "Spain", "VLC": "Spain", "SVQ": "Spain", "LIS": "Portugal", "OPO": "Portugal", "FAO": "Portugal",
    # Italy
    "FCO": "Italy", "MXP": "Italy", "VCE": "Italy", "BGY": "Italy", "NAP": "Italy", "PSA": "Italy", "BLQ": "Italy",
    # Nordic & Baltic
    "CPH": "Denmark", "OSL": "Norway", "ARN": "Sweden", "HEL": "Finland", "KEF": "Iceland", "RIX": "Latvia", "VNO": "Lithuania", "TLL": "Estonia",
    # Eastern Europe & Balkans
    "WAW": "Poland", "KRK": "Poland", "GDN": "Poland", "PRG": "Czechia", "BUD": "Hungary", "OTP": "Romania", "SOF": "Bulgaria", "BEG": "Serbia", "SKP": "North Macedonia", "TIA": "Albania", "MSQ": "Belarus", "KBP": "Ukraine",
    # Southeast
    "ATH": "Greece", "SKG": "Greece", "HER": "Greece", "IST": "Turkey", "SAW": "Turkey",

    # North America - USA
    "ATL": "USA", "LAX": "USA", "ORD": "USA", "DFW": "USA", "DEN": "USA", "JFK": "USA", "SFO": "USA", "SEA": "USA", "LAS": "USA", "MCO": "USA", "EWR": "USA", "CLT": "USA", "PHX": "USA", "IAH": "USA", "MIA": "USA", "BOS": "USA", "IAD": "USA", "DCA": "USA", "SAN": "USA", "TPA": "USA", "PHL": "USA", "MSP": "USA", "DTW": "USA", "SLC": "USA", "FLL": "USA", "BWI": "USA", "MDW": "USA",
    # Canada
    "YYZ": "Canada", "YVR": "Canada", "YUL": "Canada", "YYC": "Canada", "YEG": "Canada", "YOW": "Canada",
    # Mexico
    "MEX": "Mexico", "CUN": "Mexico", "GDL": "Mexico", "MTY": "Mexico",

    # Asia
    # Japan
    "HND": "Japan", "NRT": "Japan", "KIX": "Japan", "CTS": "Japan", "FUK": "Japan",
    "ICN": "South Korea", "SIN": "Singapore", "HKG": "Hong Kong", "BKK": "Thailand", "PVG": "China", "PEK": "China", "TPE": "Taiwan", "KUL": "Malaysia",
    "DEL": "India", "BOM": "India", "BLR": "India", "HYD": "India", "MAA": "India", "CCU": "India",
    "DXB": "UAE", "DOH": "Qatar", "AUH": "UAE", "SGN": "Vietnam", "HAN": "Vietnam", "MNL": "Philippines", "CGK": "Indonesia",
    "PKX": "China", "CAN": "China", "SZX": "China", "CTU": "China", "KMG": "China", "SHA": "China",
    "RUH": "Saudi Arabia", "JED": "Saudi Arabia", "KWI": "Kuwait", "MCT": "Oman",

    # Africa
    # Morocco
    "CMN": "Morocco", "RAK": "Morocco", "AGA": "Morocco", "TNG": "Morocco", "FEZ": "Morocco", "RBA": "Morocco", "NDR": "Morocco", "OUD": "Morocco",
    # Egypt
    "CAI": "Egypt", "HRG": "Egypt", "SSH": "Egypt", "LXR": "Egypt", "ASW": "Egypt", "RMF": "Egypt", "HBE": "Egypt", "SPX": "Egypt",
    # Algeria
    "ALG": "Algeria", "ORA": "Algeria", "AAE": "Algeria", "CZL": "Algeria",
    # Tunisia
    "TUN": "Tunisia", "DJE": "Tunisia", "MIR": "Tunisia", "SFA": "Tunisia",
    # Libya
    "TIP": "Libya", "BEN": "Libya", "MJI": "Libya",
    # Sub-Saharan
    "JNB": "South Africa", "CPT": "South Africa", "DUR": "South Africa", "HLA": "South Africa", "ADD": "Ethiopia", "NBO": "Kenya", "MBA": "Kenya", "LOS": "Nigeria", "ABV": "Nigeria", "ACC": "Ghana", "DSS": "Senegal", "DKR": "Senegal", "ABJ": "Cote d'Ivoire", "DAR": "Tanzania", "ZNZ": "Tanzania", "EBB": "Uganda", "KGL": "Rwanda", "HRE": "Zimbabwe", "MPM": "Mozambique", "LAD": "Angola",

    # Oceania
    "SYD": "Australia", "MEL": "Australia", "BNE": "Australia", "PER": "Australia", "ADL": "Australia", "OOL": "Australia", "CNS": "Australia", "AKL": "New Zealand", "CHC": "New Zealand", "WLG": "New Zealand", "NAN": "Fiji",

    # South America
    "GRU": "Brazil", "BOG": "Colombia", "SCL": "Chile", "LIM": "Peru", "EZE": "Argentina", "GIG": "Brazil", "AEP": "Argentina", "VVI": "Bolivia", "UIO": "Ecuador", "ASU": "Paraguay", "MVD": "Uruguay", "MDE": "Colombia",
}

CITY_HUBS = {
    "Paris": ["CDG", "ORY", "BVA"],
    "London": ["LHR", "LGW", "STN", "LTN", "LCY", "SEN"],
    "Milan": ["MXP", "LIN", "BGY"],
    "Istanbul": ["IST", "SAW"],
    "New York": ["JFK", "EWR", "LGA"],
    "Washington DC": ["IAD", "DCA", "BWI"],
    "Tokyo": ["HND", "NRT"],
    "Seoul": ["ICN", "GMP"],
    "Shanghai": ["PVG", "SHA"],
    "Casablanca": ["CMN", "CAS"],
    "Cairo": ["CAI", "SPX"],
    "Dubai": ["DXB", "DWC"],
    "Buenos Aires": ["EZE", "AEP"],
    "Sao Paulo": ["GRU", "CGH", "VCP"]
}

# Reverse mapping for quick lookup
AIRPORT_TO_HUB = {code: hub for hub, codes in CITY_HUBS.items() for code in codes}

def get_airports_for_region(region: str):
    """Returns all airport codes for a specific region.

    Behaviour notes:
    - Region matching is case-insensitive (e.g. 'all', 'All', 'ALL').
    - When returning all regions, preserves original ordering and removes duplicates.
    """
    if not region:
        return []

    region_normalized = region.strip().lower()
    if region_normalized == "all":
        all_airports = []
        for airports in AIRPORTS_BY_REGION.values():
            all_airports.extend(airports)
        # Preserve order while removing duplicates
        return list(dict.fromkeys(all_airports))

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

def get_airport_hub(code: str):
    """Returns the city hub name for an airport code (e.g., 'JFK' -> 'New York')."""
    return AIRPORT_TO_HUB.get(code.upper())

def get_all_regions():
    """Returns list of available regions."""
    return list(AIRPORTS_BY_REGION.keys())
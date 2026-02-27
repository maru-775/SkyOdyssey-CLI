import asyncio
import json
import datetime
import sys
import re
from urllib.parse import urlencode
from typing import Any, Optional, Dict, List, Callable
from pydantic import BaseModel

try:
    from fast_flights import FlightData, Passengers, get_flights
except ImportError as e:
    print(f"Error importing fast_flights: {e}", file=sys.stderr)
    sys.exit(1)

from airports import get_airports_excluding, AIRPORT_TO_COUNTRY, get_airport_hub

import sqlite3
import time

# --- Pydantic Models for Type Safety ---

class ItineraryLeg(BaseModel):
    origin: str
    destination: str
    date: str
    price: str
    stops: int
    carrier: Optional[str] = None
    departure: Optional[str] = None
    arrival: Optional[str] = None
    duration: Optional[str] = None
    buy_link: Optional[str] = None

class ItineraryModel(BaseModel):
    total_price: float
    origin: str
    return_destination: str
    legs: List[ItineraryLeg]
    cached: bool = False
    warning: Optional[str] = None

# --- Cache Configuration ---
CACHE_FILE = "flights_cache.db"
CACHE_TTL = 6 * 3600  # 6 hours

def init_cache():
    """Initializes the SQLite database for flight caching."""
    conn = sqlite3.connect(CACHE_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS flights
                 (key TEXT PRIMARY KEY, price_str TEXT, numeric_price REAL, flight_json TEXT, timestamp REAL)''')
    c.execute("DELETE FROM flights WHERE numeric_price IS NULL OR numeric_price <= 0")
    conn.commit()
    conn.close()

def get_cached_flight(origin, dest, date, adults, seat_type):
    """Retrieves a flight from cache if it exists and is not expired."""
    key = f"{origin}:{dest}:{date}:{adults}:{seat_type}"
    try:
        conn = sqlite3.connect(CACHE_FILE)
        c = conn.cursor()
        c.execute("SELECT price_str, numeric_price, flight_json, timestamp FROM flights WHERE key=?", (key,))
        row = c.fetchone()
        conn.close()
        if row:
            price_str, numeric_price, flight_json, timestamp = row
            if time.time() - timestamp < CACHE_TTL:
                flight_payload = json.loads(flight_json)
                if isinstance(flight_payload, dict) and not flight_payload.get("buy_link"):
                    flight_payload["buy_link"] = build_google_flights_link(origin, dest, date)
                return {
                    "destination": dest,
                    "origin": origin,
                    "date": date,
                    "price": price_str,
                    "numeric_price": numeric_price,
                    "flight": flight_payload,
                    "cached": True
                }
    except Exception as e:
        print(f"Cache read error: {e}", file=sys.stderr)
    return None

def set_cached_flight(origin, dest, date, adults, seat_type, result):
    """Stores a flight result in the cache."""
    key = f"{origin}:{dest}:{date}:{adults}:{seat_type}"
    try:
        conn = sqlite3.connect(CACHE_FILE)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO flights VALUES (?, ?, ?, ?, ?)",
                  (key, result["price"], result["numeric_price"], json.dumps(result["flight"]), time.time()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Cache write error: {e}", file=sys.stderr)

# Initialize cache on import
init_cache()

def normalize_stops(stops_value):
    """Normalizes stop values from provider payload to an integer."""
    if isinstance(stops_value, int):
        return stops_value
    if isinstance(stops_value, str):
        digits = "".join(ch for ch in stops_value if ch.isdigit())
        if digits:
            return int(digits)
    return 1

def build_google_flights_link(origin: str, destination: str, date: str) -> str:
    """Builds a Google Flights one-way search URL for quick purchase flow."""
    base = "https://www.google.com/travel/flights"
    query = urlencode({
        "hl": "en",
        "curr": "EUR",
        "gl": "fr",
        "q": f"Flights from {origin} to {destination} on {date}",
    })
    return f"{base}?{query}"

def flight_to_dict(flight):
    """Converts a flight object to a dictionary."""
    return {
        "is_best": getattr(flight, 'is_best', None),
        "name": getattr(flight, 'name', None),
        "departure": getattr(flight, 'departure', None),
        "arrival": getattr(flight, 'arrival', None),
        "arrival_time_ahead": getattr(flight, 'arrival_time_ahead', None),
        "duration": getattr(flight, 'duration', None),
        "stops": normalize_stops(getattr(flight, 'stops', None)),
        "delay": getattr(flight, 'delay', None),
        "price": getattr(flight, 'price', None),
        "airline": getattr(flight, 'name', None), # 'name' in fast_flights often contains airline
    }

def parse_price(price_str):
    """Extracts integer price from a string like '$268' or '1,200 €'."""
    if not price_str or not isinstance(price_str, str):
        return float('inf')
    try:
        clean_str = "".join(c for c in price_str if c.isdigit() or c == '.')
        if not clean_str:
            return float('inf')
        return int(float(clean_str))
    except ValueError:
        return float('inf')

def parse_clock_minutes(value: Optional[str]) -> Optional[int]:
    """Parses a time string and returns minutes since midnight."""
    if not value or not isinstance(value, str):
        return None
    match = re.search(r"(\d{1,2}:\d{2}\s*[AP]M)", value, flags=re.IGNORECASE)
    if not match:
        return None
    clock = match.group(1).upper().replace(" ", "")
    try:
        dt = datetime.datetime.strptime(clock, "%I:%M%p")
        return dt.hour * 60 + dt.minute
    except ValueError:
        return None

def parse_hhmm_minutes(value: Optional[str]) -> Optional[int]:
    """Parses HH:MM (24h) into minutes since midnight."""
    if not value:
        return None
    try:
        hours, minutes = value.split(":")
        h = int(hours)
        m = int(minutes)
        if 0 <= h <= 23 and 0 <= m <= 59:
            return h * 60 + m
    except Exception:
        return None
    return None

def parse_duration_minutes(value: Optional[str]) -> int:
    """Parses duration like '2 hr 15 min' or '45 min' into minutes."""
    if not value or not isinstance(value, str):
        return 10**9
    total = 0
    hour_match = re.search(r"(\d+)\s*hr", value, flags=re.IGNORECASE)
    min_match = re.search(r"(\d+)\s*min", value, flags=re.IGNORECASE)
    if hour_match:
        total += int(hour_match.group(1)) * 60
    if min_match:
        total += int(min_match.group(1))
    return total if total > 0 else 10**9

def expand_dates_with_flex(date_str: str, date_flex: int = 0) -> List[str]:
    """Expands a date into [date-flex, ..., date, ..., date+flex]."""
    if not date_flex or date_flex < 0:
        return [date_str]
    base = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    dates = []
    for delta in range(-date_flex, date_flex + 1):
        dates.append((base + datetime.timedelta(days=delta)).strftime("%Y-%m-%d"))
    return dates

def leg_matches_time_filters(
    leg: Dict[str, Any],
    depart_after_minutes: Optional[int] = None,
    depart_before_minutes: Optional[int] = None,
    arrive_before_minutes: Optional[int] = None,
) -> bool:
    """Checks if a leg satisfies departure/arrival time windows."""
    dep_minutes = parse_clock_minutes(leg.get("departure"))
    arr_minutes = parse_clock_minutes(leg.get("arrival"))
    if depart_after_minutes is not None and (dep_minutes is None or dep_minutes < depart_after_minutes):
        return False
    if depart_before_minutes is not None and (dep_minutes is None or dep_minutes > depart_before_minutes):
        return False
    if arrive_before_minutes is not None and (arr_minutes is None or arr_minutes > arrive_before_minutes):
        return False
    return True

def sort_basic_results(results: List[Dict[str, Any]], sort_by: str = "price"):
    """Sorts basic-mode results by selected key."""
    if sort_by == "duration":
        results.sort(key=lambda x: sum(parse_duration_minutes(leg.get("duration")) for leg in x.get("legs", [])))
    elif sort_by == "stops":
        results.sort(key=lambda x: sum(int(leg.get("stops", 0)) for leg in x.get("legs", [])))
    elif sort_by == "departure":
        results.sort(key=lambda x: parse_clock_minutes((x.get("legs") or [{}])[0].get("departure")) or 10**9)
    else:
        results.sort(key=lambda x: x.get("total_price", float("inf")))

def is_valid_price(price_value):
    """A valid fare must be a positive finite number."""
    return isinstance(price_value, (int, float)) and price_value > 0 and price_value != float('inf')

def compute_concurrency(limit_hint: int, max_concurrency: int = 4):
    """Computes a safe adaptive concurrency from search width."""
    return max(1, min(max_concurrency, (limit_hint // 2) + 1))

def build_request_key(
    origin,
    dest,
    date,
    adults,
    seat_type,
    direct_only,
    include_airlines,
    exclude_airlines,
):
    include_key = tuple(sorted(include_airlines or []))
    exclude_key = tuple(sorted(exclude_airlines or []))
    return (
        origin,
        dest,
        date,
        adults,
        seat_type,
        bool(direct_only),
        include_key,
        exclude_key,
    )

async def async_fetch_cheapest(
    origin, dest, date, semaphore, adults=1, seat_type="economy", 
    direct_only=False, include_airlines=None, exclude_airlines=None,
    debug_callback: Optional[Callable[[str], None]] = None,
    trace_label: str = "",
    inflight_requests: Optional[Dict[Any, asyncio.Task]] = None,
    retry_attempts: int = 2,
    backoff_base_seconds: float = 0.75,
):
    """Internal helper to fetch the cheapest flight between two airports with caching and advanced filtering."""
    origin = origin.upper()
    dest = dest.upper()

    # 1. Check Cache
    cached = get_cached_flight(origin, dest, date, adults, seat_type)
    
    if cached:
        f = cached["flight"]
        if not is_valid_price(cached.get("numeric_price")):
            if debug_callback:
                debug_callback(f"CACHE_DROP {trace_label} {origin}->{dest} invalid price={cached.get('numeric_price')}")
            return None
        # Apply filters to cached result
        if direct_only and f.get("stops") != 0: return None
        if include_airlines and f.get("airline") not in include_airlines: return None
        if exclude_airlines and f.get("airline") in exclude_airlines: return None
        if debug_callback:
            debug_callback(f"CACHE_HIT {trace_label} {origin}->{dest} price={cached.get('numeric_price')}")
        return cached

    async def scrape_and_cache():
        # 2. Scrape if not in cache
        async with semaphore:
            for attempt in range(retry_attempts + 1):
                try:
                    flight_data = [FlightData(date=date, from_airport=origin, to_airport=dest)]
                    passengers_info = Passengers(adults=adults)
                    res = await asyncio.to_thread(
                        get_flights,
                        flight_data=flight_data,
                        trip="one-way",
                        seat=seat_type,
                        passengers=passengers_info,
                        fetch_mode="local",
                    )
                except Exception as e:
                    error_msg = str(e)
                    is_timeout = "Timeout" in error_msg and "wait_for" in error_msg
                    if is_timeout and attempt < retry_attempts:
                        if debug_callback:
                            debug_callback(f"FETCH_RETRY {trace_label} {origin}->{dest} attempt={attempt + 1}")
                        await asyncio.sleep(backoff_base_seconds * (2 ** attempt))
                        continue

                    if is_timeout:
                        print(f"Search timed out for {origin}->{dest} (Google Flights slow response)", file=sys.stderr)
                        if debug_callback:
                            debug_callback(f"FETCH_TIMEOUT {trace_label} {origin}->{dest}")
                    else:
                        print(f"Error checking {origin}->{dest}: {error_msg}", file=sys.stderr)
                        if debug_callback:
                            debug_callback(f"FETCH_ERROR {trace_label} {origin}->{dest} err={error_msg}")
                    return None

                if res and res.flights:
                    total_flights = len(res.flights)
                    valid_flights = [
                        f for f in res.flights
                        if f.price != "Unavailable" and is_valid_price(parse_price(getattr(f, "price", None)))
                    ]
                    
                    # Apply filters
                    if direct_only:
                        valid_flights = [f for f in valid_flights if getattr(f, 'stops', None) == 0]
                    if include_airlines:
                        valid_flights = [f for f in valid_flights if getattr(f, 'name', None) in include_airlines]
                    if exclude_airlines:
                        valid_flights = [f for f in valid_flights if getattr(f, 'name', None) not in exclude_airlines]

                    if debug_callback:
                        debug_callback(
                            f"FETCH_OK {trace_label} {origin}->{dest} total={total_flights} valid={len(valid_flights)}"
                        )
                    
                    if valid_flights:
                        cheapest = min(valid_flights, key=lambda f: parse_price(f.price))
                        cheapest_price = parse_price(cheapest.price)
                        if not is_valid_price(cheapest_price):
                            if debug_callback:
                                debug_callback(f"FETCH_DROP {trace_label} {origin}->{dest} cheapest invalid={cheapest.price}")
                            return None
                        result = {
                            "destination": dest,
                            "origin": origin,
                            "date": date,
                            "price": cheapest.price,
                            "numeric_price": cheapest_price,
                            "flight": flight_to_dict(cheapest)
                        }
                        result["flight"]["buy_link"] = build_google_flights_link(origin, dest, date)
                        # 3. Update Cache
                        set_cached_flight(origin, dest, date, adults, seat_type, result)
                        if debug_callback:
                            debug_callback(f"FETCH_PICK {trace_label} {origin}->{dest} cheapest={cheapest_price} raw={cheapest.price}")
                        return result
                    if debug_callback:
                        debug_callback(f"FETCH_DROP {trace_label} {origin}->{dest} no valid flights after filters")
                return None
            return None

    request_key = build_request_key(
        origin, dest, date, adults, seat_type,
        direct_only, include_airlines, exclude_airlines
    )

    if inflight_requests is not None:
        existing_task = inflight_requests.get(request_key)
        if existing_task:
            if debug_callback:
                debug_callback(f"INFLIGHT_WAIT {trace_label} {origin}->{dest}")
            return await existing_task

        created_task = asyncio.create_task(scrape_and_cache())
        inflight_requests[request_key] = created_task
        try:
            return await created_task
        finally:
            if inflight_requests.get(request_key) is created_task:
                inflight_requests.pop(request_key, None)

    return await scrape_and_cache()

async def get_cheapest_destinations_logic(
    origin: str,
    date: str,
    region: str = "Europe",
    limit: int = 15,
    adults: int = 1,
    seat_type: str = "economy",
    excluded_countries: list = None,
    excluded_airports: list = None,
    direct_only: bool = False,
    include_airlines: list = None,
    exclude_airlines: list = None,
    debug_callback: Optional[Callable[[str], None]] = None,
    trace_label: str = "",
    inflight_requests: Optional[Dict[Any, asyncio.Task]] = None,
    concurrency: Optional[int] = None,
):
    """Business logic for exploring multiple destinations in parallel."""
    origin = origin.upper()
    destinations = get_airports_excluding(region, excluded_countries, excluded_airports)
    if not destinations:
        if debug_callback:
            debug_callback(f"DEST_EMPTY {trace_label} origin={origin} region={region}")
        return {"error": "No airports matching filters."}
    
    destinations = [d for d in destinations if d != origin][:limit]
    if debug_callback:
        debug_callback(f"DEST_LIST {trace_label} origin={origin} region={region} count={len(destinations)} limit={limit}")
    
    resolved_concurrency = concurrency if concurrency is not None else compute_concurrency(limit)
    semaphore = asyncio.Semaphore(resolved_concurrency)
    tasks = [async_fetch_cheapest(
        origin, d, date, semaphore, adults, seat_type, 
        direct_only=direct_only, include_airlines=include_airlines, exclude_airlines=exclude_airlines,
        debug_callback=debug_callback, trace_label=trace_label,
        inflight_requests=inflight_requests
    ) for d in destinations]
    parallel_results = await asyncio.gather(*tasks)
    
    results = [r for r in parallel_results if r is not None]
    results.sort(key=lambda x: x["numeric_price"])
    if debug_callback:
        debug_callback(f"DEST_RESULT {trace_label} origin={origin} kept={len(results)} concurrency={resolved_concurrency}")
    
    return {"origin": origin, "date": date, "cheapest_options": results}

async def find_cheapest_two_city_itinerary_logic(
    origin: Any, # Can be str or List[str]
    start_date: str,
    stay_days_1: Any = 2, # Can be int or list [min, max]
    stay_days_2: Any = 2, # Can be int or list [min, max]
    region: str = "Europe",
    limit_per_leg: int = 15,
    excluded_countries: list = None,
    excluded_airports: list = None,
    max_itineraries: int = 30,
    force_different_countries: bool = False,
    progress_callback: Any = None, # Optional callback for Rich UI
    direct_only: bool = False,
    return_origin: Optional[str] = None,
    include_airlines: list = None,
    exclude_airlines: list = None,
    max_budget: Optional[float] = None,
    debug: bool = False,
    debug_callback: Optional[Callable[[str], None]] = None
):
    """Business logic for finding the cheapest 3-leg loop itinerary with flexible stay ranges and multi-origin support."""
    try:
        dt_start = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        date_1 = dt_start.strftime('%Y-%m-%d')
        
        # Handle flexible stays
        def get_day_range(stay_val):
            if isinstance(stay_val, list) and len(stay_val) == 2:
                return range(stay_val[0], stay_val[1] + 1)
            return [int(stay_val)]

        stay1_range = get_day_range(stay_days_1)
        stay2_range = get_day_range(stay_days_2)

        # Handle multi-origin and normalize codes
        origins = [o.upper() for o in ([origin] if isinstance(origin, str) else list(origin))]
        normalized_return_origin = return_origin.upper() if return_origin else None

    except (ValueError, TypeError):
        return {"error": "Invalid start_date or stay_days format."}

    def dlog(message: str):
        if debug and debug_callback:
            debug_callback(message)

    stats = {
        "step1_candidates": 0,
        "step1_budget_pruned": 0,
        "step2_tasks": 0,
        "step2_candidates": 0,
        "step3_return_tasks": 0,
        "step3_budget_pruned": 0,
        "step3_missing_return": 0,
        "final_budget_pruned": 0,
        "final_itineraries": 0,
    }
    inflight_requests: Dict[Any, asyncio.Task] = {}
    destination_concurrency = compute_concurrency(limit_per_leg, max_concurrency=3)
    return_concurrency = compute_concurrency(limit_per_leg, max_concurrency=4)
    dlog(f"RUN_START origins={origins} region={region} limit={limit_per_leg} budget={max_budget}")
    dlog(f"RUN_CONCURRENCY destination={destination_concurrency} return={return_concurrency}")

    # Step 1: Broad sweep for City A candidates from ALL origins
    if progress_callback: progress_callback("Searching for primary destinations from all origins...")
    
    sweep_tasks = []
    for o in origins:
        step1_excluded = list(excluded_countries or [])
        if force_different_countries:
            origin_country = AIRPORT_TO_COUNTRY.get(o)
            if origin_country:
                step1_excluded.append(origin_country)

        sweep_tasks.append(get_cheapest_destinations_logic(
            o, date_1, region, limit=max(limit_per_leg * 2, 4), 
            excluded_countries=step1_excluded, excluded_airports=excluded_airports, 
            direct_only=direct_only, include_airlines=include_airlines, exclude_airlines=exclude_airlines,
            debug_callback=dlog, trace_label="STEP1",
            inflight_requests=inflight_requests,
            concurrency=destination_concurrency,
        ))
    
    sweep_results = await asyncio.gather(*sweep_tasks)
    
    all_candidates_a = []
    for i, res_a in enumerate(sweep_results):
        if "cheapest_options" in res_a:
            orig = origins[i]
            for opt in res_a["cheapest_options"][:limit_per_leg]:
                if max_budget and opt["numeric_price"] > max_budget:
                    stats["step1_budget_pruned"] += 1
                    continue
                opt["search_origin"] = orig # Track which origin this came from
                all_candidates_a.append(opt)
    stats["step1_candidates"] = len(all_candidates_a)
    dlog(f"STEP1_DONE candidates={stats['step1_candidates']} budget_pruned={stats['step1_budget_pruned']}")

    if not all_candidates_a:
        return {"error": "No candidates found from any origin."}
    
    # Sort and limit to best global candidates for leg 1
    all_candidates_a.sort(key=lambda x: x["numeric_price"])
    candidates_a = all_candidates_a[:limit_per_leg * len(origins)]
    
    itineraries = []
    
    # Step 2: Branch for each City A AND each possible stay duration
    if progress_callback: progress_callback(f"Exploring second leg for {len(candidates_a)} City A candidates...")
    
    second_leg_tasks = []
    task_metadata_2 = [] 

    for cand_a in candidates_a:
        city_a = cand_a["destination"]
        country_a = AIRPORT_TO_COUNTRY.get(city_a.upper())
        search_origin = cand_a["search_origin"]
        origin_country = AIRPORT_TO_COUNTRY.get(search_origin.upper())
        step2_excluded = list(excluded_countries or [])
        if force_different_countries:
            if country_a:
                step2_excluded.append(country_a)
            if origin_country:
                step2_excluded.append(origin_country)

        for s1 in stay1_range:
            date_2 = (dt_start + datetime.timedelta(days=s1)).strftime('%Y-%m-%d')
            second_leg_tasks.append(get_cheapest_destinations_logic(
                city_a, date_2, region, limit=limit_per_leg, 
                excluded_countries=step2_excluded, excluded_airports=excluded_airports, 
                direct_only=direct_only, include_airlines=include_airlines, exclude_airlines=exclude_airlines,
                debug_callback=dlog, trace_label="STEP2",
                inflight_requests=inflight_requests,
                concurrency=destination_concurrency,
            ))
            task_metadata_2.append((cand_a, s1, date_2))
            stats["step2_tasks"] += 1

    leg2_results = await asyncio.gather(*second_leg_tasks)
    
    # Step 3: Branch for each City B AND each possible stay duration
    if progress_callback: progress_callback("Calculating return legs and final prices...")
    
    return_tasks = []
    semaphore = asyncio.Semaphore(return_concurrency)
    
    for i, res_b in enumerate(leg2_results):
        if "cheapest_options" not in res_b: continue
        stats["step2_candidates"] += len(res_b.get("cheapest_options", []))
        
        cand_a, s1, _ = task_metadata_2[i]
        orig = cand_a["search_origin"]
        
        for cand_b in res_b["cheapest_options"]:
            # Ensure City B is not an origin or City A
            if cand_b["destination"] in origins or cand_b["destination"] == cand_a["destination"]: continue
            
            # Use return_origin if provided, otherwise the search origin
            ret_dest = normalized_return_origin if normalized_return_origin else orig

            for s2 in stay2_range:
                # Early Exit logic: if Leg 1 + Leg 2 already exceeds budget, don't even check the return
                current_cost = cand_a["numeric_price"] + cand_b["numeric_price"]
                if max_budget and current_cost >= max_budget:
                    stats["step3_budget_pruned"] += 1
                    continue

                date_3 = (dt_start + datetime.timedelta(days=s1 + s2)).strftime('%Y-%m-%d')
                return_tasks.append((cand_a, cand_b, async_fetch_cheapest(
                    cand_b["destination"], ret_dest, date_3, semaphore, 
                    direct_only=direct_only, include_airlines=include_airlines, exclude_airlines=exclude_airlines,
                    debug_callback=dlog, trace_label="STEP3",
                    inflight_requests=inflight_requests,
                )))
                stats["step3_return_tasks"] += 1

    dlog(
        "STEP3_PREP "
        f"step2_tasks={stats['step2_tasks']} step2_candidates={stats['step2_candidates']} "
        f"return_tasks={stats['step3_return_tasks']} pruned_budget={stats['step3_budget_pruned']}"
    )

    completed_returns = await asyncio.gather(*(t[2] for t in return_tasks))
    
    for i, res_ret in enumerate(completed_returns):
        if res_ret:
            c_a, c_b, _ = return_tasks[i]
            orig = c_a["search_origin"]
            ret_dest = normalized_return_origin if normalized_return_origin else orig
            total_price = c_a["numeric_price"] + c_b["numeric_price"] + res_ret["numeric_price"]
            
            if max_budget and total_price > max_budget:
                stats["final_budget_pruned"] += 1
                continue

            try:
                # Detect Airport Change Warnings
                warning_msg = None
                # Check Leg 1 -> Leg 2
                if c_a["destination"] != c_b["origin"]:
                    hub_a = get_airport_hub(c_a["destination"])
                    hub_b = get_airport_hub(c_b["origin"])
                    if hub_a and hub_a == hub_b:
                        warning_msg = f"Airport change required in {hub_a} ({c_a['destination']} to {c_b['origin']})"
                
                # Check Leg 2 -> Leg 3 (Return)
                if not warning_msg and c_b["destination"] != ret_dest:
                    hub_b = get_airport_hub(c_b["destination"])
                    hub_ret = get_airport_hub(ret_dest)
                    if hub_b and hub_b == hub_ret:
                        warning_msg = f"Airport change required in {hub_b} ({c_b['destination']} to {ret_dest})"

                # Validate with Pydantic
                itinerary_obj = ItineraryModel(
                    total_price=total_price,
                    origin=orig,
                    return_destination=ret_dest,
                    legs=[
                        ItineraryLeg(
                            origin=orig,
                            destination=c_a["destination"],
                            date=c_a["date"],
                            price=c_a["price"],
                            stops=normalize_stops(c_a["flight"].get("stops", 0)),
                            carrier=c_a["flight"].get("airline"),
                            departure=c_a["flight"].get("departure"),
                            arrival=c_a["flight"].get("arrival"),
                            duration=c_a["flight"].get("duration"),
                            buy_link=c_a["flight"].get("buy_link"),
                        ),
                        ItineraryLeg(
                            origin=c_a["destination"],
                            destination=c_b["destination"],
                            date=c_b["date"],
                            price=c_b["price"],
                            stops=normalize_stops(c_b["flight"].get("stops", 0)),
                            carrier=c_b["flight"].get("airline"),
                            departure=c_b["flight"].get("departure"),
                            arrival=c_b["flight"].get("arrival"),
                            duration=c_b["flight"].get("duration"),
                            buy_link=c_b["flight"].get("buy_link"),
                        ),
                        ItineraryLeg(
                            origin=c_b["destination"],
                            destination=ret_dest,
                            date=res_ret["date"],
                            price=res_ret["price"],
                            stops=normalize_stops(res_ret["flight"].get("stops", 0)),
                            carrier=res_ret["flight"].get("airline"),
                            departure=res_ret["flight"].get("departure"),
                            arrival=res_ret["flight"].get("arrival"),
                            duration=res_ret["flight"].get("duration"),
                            buy_link=res_ret["flight"].get("buy_link"),
                        )
                    ],
                    cached=any([c_a.get("cached"), c_b.get("cached"), res_ret.get("cached")]),
                    warning=warning_msg
                )
                itineraries.append(itinerary_obj.model_dump())
            except Exception as e:
                print(f"Validation error for itinerary: {e}", file=sys.stderr)
                continue
        else:
            stats["step3_missing_return"] += 1

    itineraries.sort(key=lambda x: x["total_price"])
    stats["final_itineraries"] = len(itineraries[:max_itineraries])
    dlog(
        "RUN_DONE "
        f"itineraries={stats['final_itineraries']} missing_return={stats['step3_missing_return']} "
        f"final_budget_pruned={stats['final_budget_pruned']}"
    )
    result_payload = {"itineraries": itineraries[:max_itineraries]}
    if debug:
        result_payload["debug_stats"] = stats
    return result_payload


async def fetch_route_options(
    origin: str,
    destination: str,
    date: str,
    max_results: int = 10,
    adults: int = 1,
    seat_type: str = "economy",
    direct_only: bool = False,
    include_airlines: list = None,
    exclude_airlines: list = None,
    depart_after_minutes: Optional[int] = None,
    depart_before_minutes: Optional[int] = None,
    arrive_before_minutes: Optional[int] = None,
    retry_attempts: int = 2,
    backoff_base_seconds: float = 0.75,
):
    """Fetches and normalizes multiple flight options for a direct route/date query."""
    origin = origin.upper()
    destination = destination.upper()

    res = None
    for attempt in range(retry_attempts + 1):
        try:
            flight_data = [FlightData(date=date, from_airport=origin, to_airport=destination)]
            passengers_info = Passengers(adults=adults)
            res = await asyncio.to_thread(
                get_flights,
                flight_data=flight_data,
                trip="one-way",
                seat=seat_type,
                passengers=passengers_info,
                fetch_mode="local",
            )
            break
        except Exception as e:
            error_msg = str(e)
            is_timeout = "Timeout" in error_msg and "wait_for" in error_msg
            if is_timeout and attempt < retry_attempts:
                await asyncio.sleep(backoff_base_seconds * (2 ** attempt))
                continue
            if is_timeout:
                return {"error": f"Search timed out for {origin}->{destination}."}
            return {"error": f"Error checking {origin}->{destination}: {error_msg}"}

    if not res or not res.flights:
        return {"options": []}

    options = []
    seen_options = set()
    for flight in res.flights:
        price_str = getattr(flight, "price", None)
        numeric_price = parse_price(price_str)
        if price_str == "Unavailable" or not is_valid_price(numeric_price):
            continue

        stops = normalize_stops(getattr(flight, "stops", None))
        airline = getattr(flight, "name", None)

        if direct_only and stops != 0:
            continue
        if include_airlines and airline not in include_airlines:
            continue
        if exclude_airlines and airline in exclude_airlines:
            continue

        option = {
            "origin": origin,
            "destination": destination,
            "date": date,
            "price": price_str,
            "numeric_price": numeric_price,
            "stops": stops,
            "carrier": airline,
            "departure": getattr(flight, "departure", None),
            "arrival": getattr(flight, "arrival", None),
            "duration": getattr(flight, "duration", None),
            "buy_link": build_google_flights_link(origin, destination, date),
        }
        if not leg_matches_time_filters(
            option,
            depart_after_minutes=depart_after_minutes,
            depart_before_minutes=depart_before_minutes,
            arrive_before_minutes=arrive_before_minutes,
        ):
            continue
        signature = (
            option["carrier"],
            option["departure"],
            option["arrival"],
            option["duration"],
            option["price"],
            option["stops"],
        )
        if signature in seen_options:
            continue
        seen_options.add(signature)
        options.append(option)

    options.sort(key=lambda x: x["numeric_price"])
    return {"options": options[:max_results]}


async def find_basic_flights_logic(
    origin: str,
    destination: str,
    date: str,
    return_date: Optional[str] = None,
    max_results: int = 10,
    direct_only: bool = False,
    include_airlines: list = None,
    exclude_airlines: list = None,
    max_budget: Optional[float] = None,
    sort_by: str = "price",
    date_flex: int = 0,
    depart_after_minutes: Optional[int] = None,
    depart_before_minutes: Optional[int] = None,
    arrive_before_minutes: Optional[int] = None,
    retry_attempts: int = 2,
    backoff_base_seconds: float = 0.75,
):
    """Basic search mode for one-way or round-trip flight discovery."""
    origin = origin.upper()
    destination = destination.upper()

    outbound_options = []
    outbound_dates = expand_dates_with_flex(date, date_flex)
    for outbound_date in outbound_dates:
        outbound = await fetch_route_options(
            origin=origin,
            destination=destination,
            date=outbound_date,
            max_results=max_results,
            direct_only=direct_only,
            include_airlines=include_airlines,
            exclude_airlines=exclude_airlines,
            depart_after_minutes=depart_after_minutes,
            depart_before_minutes=depart_before_minutes,
            arrive_before_minutes=arrive_before_minutes,
            retry_attempts=retry_attempts,
            backoff_base_seconds=backoff_base_seconds,
        )
        if "error" in outbound:
            continue
        outbound_options.extend(outbound.get("options", []))

    if not outbound_options:
        return {"mode": "one-way" if not return_date else "round-trip", "results": []}

    outbound_options.sort(key=lambda x: x["numeric_price"])

    if not return_date:
        results = []
        over_budget = []
        for leg in outbound_options:
            if max_budget and leg["numeric_price"] > max_budget:
                over_budget.append({"total_price": leg["numeric_price"], "legs": [leg]})
                continue
            results.append({
                "total_price": leg["numeric_price"],
                "legs": [leg],
            })
        sort_basic_results(results, sort_by)
        payload = {"mode": "one-way", "results": results[:max_results]}
        if not payload["results"] and max_budget and over_budget:
            sort_basic_results(over_budget, sort_by)
            payload["no_result_hint"] = {
                "reason": "budget",
                "cheapest_total": over_budget[0]["total_price"],
                "closest_alternatives": over_budget[:3],
            }
        return payload

    inbound_options = []
    inbound_dates = expand_dates_with_flex(return_date, date_flex)
    for inbound_date in inbound_dates:
        inbound = await fetch_route_options(
            origin=destination,
            destination=origin,
            date=inbound_date,
            max_results=max_results,
            direct_only=direct_only,
            include_airlines=include_airlines,
            exclude_airlines=exclude_airlines,
            depart_after_minutes=depart_after_minutes,
            depart_before_minutes=depart_before_minutes,
            arrive_before_minutes=arrive_before_minutes,
            retry_attempts=retry_attempts,
            backoff_base_seconds=backoff_base_seconds,
        )
        if "error" in inbound:
            continue
        inbound_options.extend(inbound.get("options", []))

    if not inbound_options:
        return {"mode": "round-trip", "results": []}

    inbound_options.sort(key=lambda x: x["numeric_price"])

    combined = []
    over_budget = []
    seen_combinations = set()
    for leg_out in outbound_options:
        for leg_in in inbound_options:
            total_price = leg_out["numeric_price"] + leg_in["numeric_price"]
            if max_budget and total_price > max_budget:
                over_budget.append({"total_price": total_price, "legs": [leg_out, leg_in]})
                continue
            combo_signature = (
                leg_out["carrier"], leg_out["departure"], leg_out["arrival"], leg_out["price"],
                leg_in["carrier"], leg_in["departure"], leg_in["arrival"], leg_in["price"],
            )
            if combo_signature in seen_combinations:
                continue
            seen_combinations.add(combo_signature)
            combined.append({
                "total_price": total_price,
                "legs": [leg_out, leg_in],
            })

    sort_basic_results(combined, sort_by)
    payload = {"mode": "round-trip", "results": combined[:max_results]}
    if not payload["results"] and max_budget and over_budget:
        sort_basic_results(over_budget, sort_by)
        payload["no_result_hint"] = {
            "reason": "budget",
            "cheapest_total": over_budget[0]["total_price"],
            "closest_alternatives": over_budget[:3],
        }
    return payload


async def find_anywhere_flights_logic(
    origin: str,
    date: str,
    region: str = "All",
    max_results: int = 10,
    limit: int = 10,
    direct_only: bool = False,
    include_airlines: list = None,
    exclude_airlines: list = None,
    excluded_countries: list = None,
    excluded_airports: list = None,
    max_budget: Optional[float] = None,
    sort_by: str = "price",
    date_flex: int = 0,
    depart_after_minutes: Optional[int] = None,
    depart_before_minutes: Optional[int] = None,
    arrive_before_minutes: Optional[int] = None,
    retry_attempts: int = 2,
    backoff_base_seconds: float = 0.75,
):
    """Basic one-leg 'anywhere' mode (origin -> many destinations)."""
    origin = origin.upper()
    search_width = max(limit * 3, max_results)
    inflight_requests: Dict[Any, asyncio.Task] = {}

    all_options = []
    for search_date in expand_dates_with_flex(date, date_flex):
        result = await get_cheapest_destinations_logic(
            origin=origin,
            date=search_date,
            region=region,
            limit=search_width,
            excluded_countries=excluded_countries,
            excluded_airports=excluded_airports,
            direct_only=direct_only,
            include_airlines=include_airlines,
            exclude_airlines=exclude_airlines,
            inflight_requests=inflight_requests,
            concurrency=compute_concurrency(search_width, max_concurrency=3),
        )
        if "error" in result:
            continue
        all_options.extend(result.get("cheapest_options", []))

    if not all_options:
        return {"mode": "anywhere", "results": []}

    options = []
    over_budget = []
    for opt in all_options:
        if max_budget and opt["numeric_price"] > max_budget:
            over_budget.append({"total_price": opt["numeric_price"], "legs": [{
                "origin": origin,
                "destination": opt["destination"],
                "date": opt["date"],
                "price": opt["price"],
                "numeric_price": opt["numeric_price"],
                "stops": normalize_stops((opt.get("flight") or {}).get("stops", 0)),
                "carrier": (opt.get("flight") or {}).get("airline"),
                "departure": (opt.get("flight") or {}).get("departure"),
                "arrival": (opt.get("flight") or {}).get("arrival"),
                "duration": (opt.get("flight") or {}).get("duration"),
                "buy_link": (opt.get("flight") or {}).get("buy_link") or build_google_flights_link(origin, opt["destination"], opt["date"]),
            }]})
            continue

        flight = opt.get("flight", {})
        leg = {
            "origin": origin,
            "destination": opt["destination"],
            "date": opt["date"],
            "price": opt["price"],
            "numeric_price": opt["numeric_price"],
            "stops": normalize_stops(flight.get("stops", 0)),
            "carrier": flight.get("airline"),
            "departure": flight.get("departure"),
            "arrival": flight.get("arrival"),
            "duration": flight.get("duration"),
            "buy_link": flight.get("buy_link") or build_google_flights_link(origin, opt["destination"], opt["date"]),
        }
        if not leg_matches_time_filters(
            leg,
            depart_after_minutes=depart_after_minutes,
            depart_before_minutes=depart_before_minutes,
            arrive_before_minutes=arrive_before_minutes,
        ):
            continue
        options.append({
            "total_price": leg["numeric_price"],
            "legs": [leg],
        })

    sort_basic_results(options, sort_by)
    payload = {"mode": "anywhere", "results": options[:max_results]}
    if not payload["results"] and max_budget and over_budget:
        sort_basic_results(over_budget, sort_by)
        payload["no_result_hint"] = {
            "reason": "budget",
            "cheapest_total": over_budget[0]["total_price"],
            "closest_alternatives": over_budget[:3],
        }
    return payload

# SkyOdyssey CLI

SkyOdyssey CLI helps you discover affordable flights in two modes:

It supports country/airport/airline filters, budget constraints, adaptive concurrency, caching, and debug tracing.

It now has two modes:

- Basic mode (one-way / round-trip / anywhere)
- Odyssey mode (advanced 3-leg loop optimizer) via `--odyssey`

---

## Features

- Multi-city itinerary search with configurable stay durations
- Basic one-way and round-trip search mode
- Basic sorting (`price|duration|stops|departure`)
- Time-window filters (`depart-after`, `depart-before`, `arrive-before`)
- Date flexibility (`--date-flex`)
- Single or multi-origin search
- Country and airport exclusion filters
- Airline include/exclude filters
- `--different-countries` enforcement across legs
- Budget-aware pruning (`--max-budget`)
- Adaptive concurrency for better performance at higher `--limit`
- In-flight request deduplication (avoids duplicate fetches during a run)
- SQLite cache (`flights_cache.db`) with TTL
- Rich terminal output with:
  - Carrier
  - Departure/arrival times
  - Duration
  - Buy link per leg
- Debug mode and debug log export
- JSON/CSV export

---

## Requirements

- Python 3.10+
- Windows/macOS/Linux
- Internet access (Google Flights scraping via `fast-flights`)

---

## Installation

### Option A: Install from local project (recommended)

From `SkyOdyssey-CLI`:

```bash
python -m pip install -e .
```

Then run:

```bash
skyodyssey --help
```

### Option B: Run directly without installing entrypoint

From `SkyOdyssey-CLI`:

```bash
python main.py --help
```

---

## Quick Start

```bash
skyodyssey --origin LYS --date 2026-04-19
```

If you use `python main.py`, run the same flags after the script name.

---

## Core Concepts

### Search modes

- **Basic mode (default)**
  - Anywhere one-leg: `--origin --date` (or explicitly `--anywhere`)
  - One-way: `--origin --destination --date`
  - Round-trip: add `--return-date`
- **Odyssey mode**: add `--odyssey`
  - Advanced 3-leg itinerary optimization with stays and branching

### Itinerary shape

SkyOdyssey searches for 3-leg loops:

- Leg 1: Origin -> City A
- Leg 2: City A -> City B
- Leg 3: City B -> Return (default origin, or `--return-origin`)

### Branching (`--limit`)

`--limit` controls search width at each stage:

- Higher value: broader search, better chance of finding strong routes, slower runtime
- Lower value: faster search, but may miss good combinations

### Budget pruning (`--max-budget`)

The search prunes aggressively:

- If leg1 + leg2 already exceeds budget, leg3 is skipped
- Completed itineraries over budget are dropped

If your budget is tight, getting no results is expected even when valid flights exist.

---

## Command-Line Options

```text
--origin               Single origin IATA code (default: LYS)
--destination          Destination IATA code (enables basic mode)
--anywhere             Basic single-leg mode from origin to any destination
--odyssey              Enable advanced 3-leg Odyssey mode
--multi-origin         Multiple origins (space-separated)
--date                 Start date YYYY-MM-DD
--return-date          Return date YYYY-MM-DD (basic round-trip)

--stay1                Fixed stay in City A
--min-stay1            Min stay in City A (default: 2)
--max-stay1            Max stay in City A

--stay2                Fixed stay in City B
--min-stay2            Min stay in City B (default: 2)
--max-stay2            Max stay in City B

--region               Search region (default: All)
--limit                Branching limit per leg (default: 3)
--sort                 Basic mode sorting: price|duration|stops|departure
--depart-after         HH:MM 24h time filter (basic modes)
--depart-before        HH:MM 24h time filter (basic modes)
--arrive-before        HH:MM 24h time filter (basic modes)
--date-flex            Search ±N days around date (basic modes)
--exclude-countries    Countries to exclude
--exclude-airports     Airports to exclude
--max-results          Max itineraries to display (default: 10)
--different-countries  Force different countries for routing logic
--direct               Only direct flights

--return-origin        Return to a different airport (open-jaw)
--include-airlines     Include only selected airlines
--exclude-airlines     Exclude selected airlines

--max-budget           Maximum total itinerary price
--deal-threshold       Highlight deals under threshold

--export               Output file (.json or .csv)
--debug                Verbose debug traces
--debug-log            Write debug traces to a file
```

---

## Examples

### 1) Basic anywhere search (default)

```bash
skyodyssey --origin LYS --date 2026-04-19
```

### 1b) Basic one-way search

```bash
skyodyssey --origin LYS --destination DUB --date 2026-04-19 --max-results 5
```

### 1c) Basic round-trip search

```bash
skyodyssey --origin LYS --destination DUB --date 2026-04-19 --return-date 2026-04-23 --max-results 5
```

### 1d) Basic anywhere search (no destination)

```bash
skyodyssey --origin LYS --date 2026-04-19 --anywhere --max-results 10 --max-budget 200
```

### 1e) Basic search with sort/time/date-flex

```bash
skyodyssey --origin LYS --destination DUB --date 2026-04-19 --return-date 2026-04-23 --date-flex 1 --sort duration --depart-after 08:00 --arrive-before 23:30
```

### 2) Fixed stays + budget + different countries

```bash
skyodyssey --origin LYS --date 2026-04-19 --odyssey --stay1 2 --stay2 2 --different-countries --max-budget 220
```

### 3) Exclude countries and airports

```bash
skyodyssey --origin LYS --date 2026-04-19 --exclude-countries italy germany --exclude-airports CDG ORY
```

### 4) Only direct flights with airline filter

```bash
skyodyssey --origin LYS --date 2026-04-19 --direct --include-airlines Ryanair easyJet
```

### 5) Open-jaw return airport

```bash
skyodyssey --origin LYS --odyssey --return-origin GVA --date 2026-04-19 --stay1 3
```

### 6) Debug run + save logs

```bash
skyodyssey --origin LYS --date 2026-04-19 --odyssey --stay1 2 --limit 10 --debug --debug-log debug_run.log
```

### 7) Export results

```bash
skyodyssey --origin LYS --date 2026-04-19 --export results.json
skyodyssey --origin LYS --date 2026-04-19 --export results.csv
```

---

## Output Format

Each result row contains:

- Total price
- Origin and return airport
- Per-leg details:
  - Route and price
  - Stops
  - Carrier
  - Departure -> arrival times
  - Duration
  - Buy link

`Buy` links are generated Google Flights search URLs for that leg's route/date.

---

## Performance Tuning

For faster results at larger search widths:

1. Start with moderate `--limit` (`3-8`), then increase
2. Use `--max-budget` to prune expensive branches early
3. Use `--direct` if your use case allows
4. Warm cache with a smaller run, then run broader search
5. Use `--debug` to inspect where pruning is happening

Notes:

- Search speed depends heavily on provider latency and anti-bot behavior
- Timeouts can still occur for some routes; the run continues where possible
- Timeout requests are retried automatically with backoff

---

## Caching

- Cache database: `flights_cache.db`
- TTL: 6 hours
- Invalid cached prices (`<= 0`) are cleaned automatically

You can remove cache manually if needed:

```bash
# from SkyOdyssey-CLI
rm flights_cache.db        # macOS/Linux
# or
del flights_cache.db       # Windows (cmd)
Remove-Item flights_cache.db  # Windows PowerShell
```

---

## Troubleshooting

### No itineraries found

Common causes:

- `--max-budget` too strict
- `--different-countries` + exclusions make search space too narrow
- `--direct` removes too many options
- Route/date genuinely has low availability

What to try:

- Increase `--max-budget`
- Lower restrictions (`--direct`, exclusions)
- Increase `--limit`
- Use `--debug` to inspect stage-by-stage pruning

For basic modes, SkyOdyssey also prints budget guidance:

- Cheapest result above your budget
- Closest alternatives so you can adjust constraints quickly

### Timeouts

- Some provider requests may timeout; this can be normal
- Retry run (cache helps on second pass)
- Use moderate `--limit` if provider is unstable

### Weird/invalid prices

- SkyOdyssey filters non-positive fares
- Legacy invalid cache rows are purged at startup

---

## Development

Project layout:

```text
SkyOdyssey-CLI/
  airports.py      # airport datasets and regional/country filtering
  logic.py         # itinerary search logic, caching, fetch, pruning
  main.py          # CLI parsing, progress UI, rendering, export
  pyproject.toml   # package metadata + console entrypoint
  requirements.txt
```

Run directly:

```bash
python main.py --help
```

Run installed entrypoint:

```bash
skyodyssey --help
```

---

## License

See `LICENSE` in this directory.

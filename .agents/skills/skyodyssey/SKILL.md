---
name: skyodyssey
version: 1.1.0
description: "Expert flight search and itinerary optimization using SkyOdyssey-CLI."
metadata:
  category: "travel"
  requires:
    bins: ["python"]
    files: ["main.py"]
  cliHelp: "python main.py --help"
---

# SkyOdyssey CLI Usage Guide

SkyOdyssey is a powerful flight search tool that scrapes real-time data from Google Flights. It supports single-route searches and a complex "Odyssey Mode" for multi-city budget travel.

## Core Concepts

### 1. Basic Search
Query direct flights between two cities or from one city to a broad region/country.

```bash
# Search from Lyon to anyone in Morocco
python main.py --origin LYS --date 2026-04-19 --region "Morocco" --limit 10
```

### 2. Odyssey Mode (`--odyssey`)
Finds the cheapest 3-leg loop itineraries (Origin -> City A -> City B -> Return). This uses a high-performance **Graph-Based search** algorithm.

```bash
# The "Sweet Spot" command for multi-country budget loops
python main.py --origin LYS --date 2026-04-19 --odyssey \
  --stay1 3 --stay2 3 --limit 50 \
  --region "Europe,Morocco,Tunisia" \
  --direct --different-countries --dedupe-cities \
  --max-budget 150 --max-results 20
```

## Parameter Reference

| Flag | Purpose | Recommended Value |
|------|---------|-------------------|
| `--origin` | Starting IATA code | `LYS`, `CDG`, etc. |
| `--region` | Target areas | `"Europe"`, `"Morocco,Turkey"` |
| `--limit` | Depth of search | `50` (Sweet spot for speed/results) |
| `--max-budget` | Total trip cost cap | `150` |
| `--odyssey` | Enable 3-leg search | Use for loops |
| `--stay1 / --stay2` | Days spent at each stop | `3` or `3-5` |
| `--different-countries` | Force international hops | Highly recommended |
| `--dedupe-cities` | One result per city pair | Keeps output clean |
| `--search-concurrency` | Network thread count | `15` (Fast/Stable) |

## Best Practices

### Speed vs. Reliability
- **For a quick check**: Use `--limit 30`. Completes in ~10-15s.
- **For a deep dive**: Use `--limit 60-80`. Finds hidden gems like CFU (Corfu) or smaller regional airports.
- **Always use `--debug`** if the search feels stuck to see real-time progress.

### Budget Management
- In Odyssey mode, Leg 1 should ideally be < 40% of your budget. If Leg 1 is too expensive, the tool will "prune" (skip) checking subsequent legs to save time.

### Airport Changes
- The tool detects if you land at one airport (e.g., ORY) and need to depart from another (e.g., CDG) in the same city. These are highlighted as **Airport change required** warnings.

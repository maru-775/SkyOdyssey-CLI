import asyncio
import argparse
import sys
import os
import json
import csv

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from logic import (
        find_cheapest_two_city_itinerary_logic,
        find_basic_flights_logic,
        find_anywhere_flights_logic,
        parse_hhmm_minutes,
    )
except ImportError as e:
    print(f"Error: Could not import core dependencies. {e}")
    sys.exit(1)

console = Console()


def export_results(itineraries: list, path: str):
    """Exports results to JSON or CSV."""
    if path.endswith(".json"):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(itineraries, f, indent=2)
        console.print(f"[bold green]Exported to {path}[/bold green]")
    elif path.endswith(".csv"):
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Option",
                "Total Price",
                "Mode",
                "Leg #",
                "Leg Origin",
                "Leg Destination",
                "Date",
                "Price",
                "Carrier",
                "Departure",
                "Arrival",
                "Duration",
                "Stops",
                "Buy Link",
            ])
            for i, item in enumerate(itineraries):
                mode = item.get("mode", "odyssey")
                for leg_index, leg in enumerate(item.get("legs", []), start=1):
                    writer.writerow([
                        i + 1,
                        item.get("total_price", ""),
                        mode,
                        leg_index,
                        leg.get("origin", ""),
                        leg.get("destination", ""),
                        leg.get("date", ""),
                        leg.get("price", ""),
                        leg.get("carrier", ""),
                        leg.get("departure", ""),
                        leg.get("arrival", ""),
                        leg.get("duration", ""),
                        leg.get("stops", ""),
                        leg.get("buy_link", ""),
                    ])
        console.print(f"[bold green]Exported to {path}[/bold green]")
    else:
        console.print(f"[bold red]Unsupported export format: {path}[/bold red]")


async def async_main():
    parser = argparse.ArgumentParser(description="SkyOdyssey Premium CLI")
    parser.add_argument("--origin", default="LYS", help="Single origin airport")
    parser.add_argument("--destination", help="Destination airport for basic one-way/round-trip mode")
    parser.add_argument("--anywhere", action="store_true", help="Basic one-leg mode: search flights from origin to any destination")
    parser.add_argument("--odyssey", action="store_true", help="Enable advanced 3-leg Odyssey mode")
    parser.add_argument("--multi-origin", nargs="+", help="Multiple origin airports")
    parser.add_argument("--date", default="2026-04-19", help="Start date YYYY-MM-DD")
    parser.add_argument("--return-date", help="Return date YYYY-MM-DD (enables round-trip in basic mode)")

    parser.add_argument("--stay1", type=int, help="Fixed stay days in city 1")
    parser.add_argument("--min-stay1", type=int, default=2, help="Min stay days in city 1")
    parser.add_argument("--max-stay1", type=int, help="Max stay days in city 1")

    parser.add_argument("--stay2", type=int, help="Fixed stay days in city 2")
    parser.add_argument("--min-stay2", type=int, default=2, help="Min stay days in city 2")
    parser.add_argument("--max-stay2", type=int, help="Max stay days in city 2")

    parser.add_argument("--region", default="All", help="Region to search (default: All)")
    parser.add_argument("--limit", type=int, default=3, help="Limit branching")
    parser.add_argument("--sort", choices=["price", "duration", "stops", "departure"], default="price", help="Sort key for basic mode")
    parser.add_argument("--depart-after", help="Filter flights departing after HH:MM (24h)")
    parser.add_argument("--depart-before", help="Filter flights departing before HH:MM (24h)")
    parser.add_argument("--arrive-before", help="Filter flights arriving before HH:MM (24h)")
    parser.add_argument("--date-flex", type=int, default=0, help="Flexible date search ±N days for basic modes")
    parser.add_argument("--exclude-countries", nargs="+", help="Exclude countries")
    parser.add_argument("--exclude-airports", nargs="+", help="Exclude airports")
    parser.add_argument("--max-results", type=int, default=10, help="Number of itineraries to show")
    parser.add_argument("--different-countries", action="store_true", help="Force different countries for City B")
    parser.add_argument("--direct", action="store_true", help="Only show direct flights (no layovers)")
    parser.add_argument("--return-origin", help="Return to a different airport (Open-Jaw)")
    parser.add_argument("--include-airlines", nargs="+", help="Only search these airlines")
    parser.add_argument("--exclude-airlines", nargs="+", help="Exclude these airlines")
    parser.add_argument("--export", help="Export path (e.g. results.json or results.csv)")
    parser.add_argument("--max-budget", type=float, help="Maximum total price for the trip")
    parser.add_argument("--search-concurrency", type=int, help="Override async concurrency for odyssey searches")
    parser.add_argument("--step1-multiplier", type=float, default=1.0, help="Step1 breadth multiplier for odyssey mode")
    parser.add_argument("--max-cityb-per-citya", type=int, default=8, help="Cap City B candidates per City A in odyssey mode")
    parser.add_argument("--early-return-buffer", type=float, default=25.0, help="Minimum remaining budget before checking return leg in odyssey mode")
    parser.add_argument("--deal-threshold", type=float, help="Highlight itineraries under this price")
    parser.add_argument("--debug", action="store_true", help="Enable verbose debug logs")
    parser.add_argument("--debug-log", help="Optional path to write debug logs")

    args = parser.parse_args()

    origins = [o.upper() for o in (args.multi_origin if args.multi_origin else [args.origin])]
    if args.destination:
        args.destination = args.destination.upper()
    if args.return_origin:
        args.return_origin = args.return_origin.upper()
    if args.exclude_airports:
        args.exclude_airports = [a.upper() for a in args.exclude_airports]

    depart_after_minutes = parse_hhmm_minutes(args.depart_after)
    depart_before_minutes = parse_hhmm_minutes(args.depart_before)
    arrive_before_minutes = parse_hhmm_minutes(args.arrive_before)

    debug_lines = []

    def debug_log(message: str):
        line = f"[DEBUG] {message}"
        debug_lines.append(line)
        if args.debug:
            console.print(f"[dim]{line}[/dim]")

    def get_stay_param(fixed, p_min, p_max):
        if fixed is not None:
            return fixed
        if p_max is not None:
            return [p_min, p_max]
        return p_min

    stay1 = get_stay_param(args.stay1, args.min_stay1, args.max_stay1)
    stay2 = get_stay_param(args.stay2, args.min_stay2, args.max_stay2)

    console.print(
        Panel.fit(
            f"[bold blue]SkyOdyssey Premium CLI[/bold blue]\n"
            f"Origins: {', '.join(origins)}\n"
            f"Return To: {args.return_origin if args.return_origin else 'Direct hub'}\n"
            f"Start: {args.date} | Stays: {stay1}, {stay2} | Region: {args.region}\n"
            f"Filters: {'Direct Only' if args.direct else 'All Flights'}\n"
            f"Budget: {f'{args.max_budget} €' if args.max_budget else 'No Limit'}",
            title="Search Configuration",
            border_style="magenta",
        )
    )

    run_basic_anywhere_mode = not args.destination and (args.anywhere or not args.odyssey)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as progress:
        main_task = progress.add_task("[cyan]Searching flights...", total=None)

        def update_progress(msg):
            progress.update(main_task, description=f"[cyan]{msg}")

        if args.destination:
            result = await find_basic_flights_logic(
                origin=origins[0],
                destination=args.destination,
                date=args.date,
                return_date=args.return_date,
                max_results=args.max_results,
                direct_only=args.direct,
                include_airlines=args.include_airlines,
                exclude_airlines=args.exclude_airlines,
                max_budget=args.max_budget,
                sort_by=args.sort,
                date_flex=args.date_flex,
                depart_after_minutes=depart_after_minutes,
                depart_before_minutes=depart_before_minutes,
                arrive_before_minutes=arrive_before_minutes,
            )
        elif run_basic_anywhere_mode:
            result = await find_anywhere_flights_logic(
                origin=origins[0],
                date=args.date,
                region=args.region,
                max_results=args.max_results,
                limit=args.limit,
                direct_only=args.direct,
                include_airlines=args.include_airlines,
                exclude_airlines=args.exclude_airlines,
                excluded_countries=args.exclude_countries,
                excluded_airports=args.exclude_airports,
                max_budget=args.max_budget,
                sort_by=args.sort,
                date_flex=args.date_flex,
                depart_after_minutes=depart_after_minutes,
                depart_before_minutes=depart_before_minutes,
                arrive_before_minutes=arrive_before_minutes,
            )
        else:
            result = await find_cheapest_two_city_itinerary_logic(
                origin=origins,
                start_date=args.date,
                stay_days_1=stay1,
                stay_days_2=stay2,
                region=args.region,
                limit_per_leg=args.limit,
                excluded_countries=args.exclude_countries,
                excluded_airports=args.exclude_airports,
                max_itineraries=args.max_results,
                force_different_countries=args.different_countries,
                progress_callback=update_progress,
                direct_only=args.direct,
                return_origin=args.return_origin,
                include_airlines=args.include_airlines,
                exclude_airlines=args.exclude_airlines,
                max_budget=args.max_budget,
                search_concurrency=args.search_concurrency,
                step1_multiplier=args.step1_multiplier,
                max_cityb_per_citya=args.max_cityb_per_citya,
                early_return_buffer=args.early_return_buffer,
                debug=args.debug,
                debug_callback=debug_log,
            )

    if args.debug_log and debug_lines:
        with open(args.debug_log, "w", encoding="utf-8") as f:
            f.write("\n".join(debug_lines) + "\n")

    if args.debug and result.get("debug_stats"):
        console.print(Panel.fit(json.dumps(result["debug_stats"], indent=2), title="Debug Summary", border_style="yellow"))

    if "error" in result:
        console.print(f"[bold red]Error:[/bold red] {result['error']}")
        return

    if args.destination or run_basic_anywhere_mode:
        basic_results = result.get("results", [])
        if not basic_results:
            console.print("[yellow]No flights found with current filters.[/yellow]")
            hint = result.get("no_result_hint")
            if hint:
                console.print(
                    f"[yellow]Cheapest over budget:[/yellow] [bold]{hint.get('cheapest_total'):.1f} €[/bold]"
                )
                alternatives = hint.get("closest_alternatives", [])
                if alternatives:
                    console.print("[yellow]Closest alternatives:[/yellow]")
                    for alt in alternatives:
                        legs = alt.get("legs", [])
                        if not legs:
                            continue
                        leg_summary = " | ".join(
                            f"{leg.get('origin')}->{leg.get('destination')} {leg.get('price')}"
                            for leg in legs
                        )
                        console.print(f"- {alt.get('total_price'):.1f} € :: {leg_summary}")
            if args.export:
                export_results([], args.export)
            return

        table = Table(
            title=f"Top {len(basic_results)} Basic Flight Options ({result.get('mode', 'one-way')})",
            show_lines=True,
            header_style="bold cyan",
        )
        table.add_column("#", justify="right", style="cyan")
        table.add_column("Total Price", justify="right", style="bold green")
        table.add_column("Trip")

        for i, item in enumerate(basic_results):
            details = ""
            item["mode"] = result.get("mode", "basic")
            for leg in item["legs"]:
                stops_str = " (Direct)" if leg.get("stops") == 0 else f" ({leg.get('stops')} stops)"
                carrier = leg.get("carrier") or "Unknown carrier"
                dep = leg.get("departure") or "?"
                arr = leg.get("arrival") or "?"
                duration = leg.get("duration") or "n/a"
                link = leg.get("buy_link")
                link_part = f" | [link={link}]Buy[/link]" if link else ""
                details += (
                    f"* {leg['date']}: [bold]{leg['origin']}[/bold] -> [bold]{leg['destination']}[/bold] ({leg['price']}){stops_str}\n"
                    f"  Carrier: {carrier} | Time: {dep} -> {arr} | Duration: {duration}{link_part}\n"
                )

            table.add_row(str(i + 1), f"{item['total_price']:.1f} €", details.strip())

        console.print(table)
        if args.export:
            export_results(basic_results, args.export)
        return

    itineraries = result.get("itineraries", [])
    if not itineraries:
        console.print("[yellow]No itineraries found with current filters.[/yellow]")
        return

    table = Table(title=f"Top {len(itineraries)} Cheapest Itineraries", show_lines=True, header_style="bold green")
    table.add_column("#", justify="right", style="cyan")
    table.add_column("Total Price", justify="right", style="bold green")
    table.add_column("Origin", justify="center")
    table.add_column("Itinerary Details")
    table.add_column("Status", justify="center")

    for i, item in enumerate(itineraries):
        details = ""
        for leg in item["legs"]:
            stops_str = " (Direct)" if leg.get("stops") == 0 else f" ({leg.get('stops')} stops)"
            carrier = leg.get("carrier") or "Unknown carrier"
            dep = leg.get("departure") or "?"
            arr = leg.get("arrival") or "?"
            duration = leg.get("duration") or "n/a"
            buy_link = leg.get("buy_link")
            link_part = f" | [link={buy_link}]Buy[/link]" if buy_link else ""
            details += (
                f"* {leg['date']}: [bold]{leg['origin']}[/bold] -> [bold]{leg['destination']}[/bold] ({leg['price']}){stops_str}\n"
                f"  Carrier: {carrier} | Time: {dep} -> {arr} | Duration: {duration}{link_part}\n"
            )

        status = "[blue]CACHED[/blue]" if item.get("cached") else "[dim]FRESH[/dim]"
        if item.get("warning"):
            status = f"{status}\n[bold red]WARNING:[/bold red]\n[red]{item['warning']}[/red]"

        price_display = f"{item['total_price']:.1f} €"
        if args.deal_threshold and item["total_price"] <= args.deal_threshold:
            price_display = f"[bold yellow]DEAL: {price_display}[/bold yellow]"
            status = f"{status}\n[bold yellow]GREAT PRICE[/bold yellow]"

        table.add_row(
            str(i + 1),
            price_display,
            f"{item['origin']} -> {item['return_destination']}",
            details.strip(),
            status,
        )

    console.print(table)

    if args.export:
        export_results(itineraries, args.export)


def main():
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Interrupted by user. Exiting...[/bold yellow]")
        sys.exit(0)


if __name__ == "__main__":
    main()

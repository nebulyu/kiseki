import argparse

from route_schema import RouteConfig
from routes import RouteConfigError, load_routes


def register_route_commands(subparsers) -> None:
    parser = subparsers.add_parser(
        "route", help="View local goal and route configuration (no API or diary DB)."
    )
    commands = parser.add_subparsers(dest="route_command", required=True)
    commands.add_parser("list", help="List all configured routes and goal statuses.")
    show_parser = commands.add_parser("show", help="Show a route and its goal definition.")
    show_parser.add_argument("route_id")


def list_routes(config: RouteConfig) -> None:
    print("Route configuration (no analysis results).")
    if not config.routes:
        print("No routes configured. Add a YAML definition under private/routes/ when ready.")
        return

    print("ROUTE ID | NAME | GOAL ID | GOAL NAME | GOAL STATUS | ROUTE STATUS")
    for route_id in sorted(config.routes):
        route = config.routes[route_id]
        goal = config.goals[route.goal_id]
        print(" | ".join(
            " ".join(value.split())
            for value in (route.id, route.name, goal.id, goal.name, goal.status, route.status)
        ))


def _print_items(label: str, items: list[str]) -> None:
    print(f"{label}:")
    if not items:
        print("  (none configured)")
    for item in items:
        print(f"  - {item}")


def show_route(config: RouteConfig, route_id: str) -> None:
    route = config.routes.get(route_id)
    if route is None:
        raise SystemExit(f"Route '{route_id}' not found. Use 'route list' to see configured IDs.")
    goal = config.goals[route.goal_id]

    print("Route configuration (no analysis results).")
    print(f"Goal: {goal.id} | {goal.name}")
    print(f"Goal status: {goal.status}")
    print(f"Goal content version: {goal.version}")
    print(f"Description: {goal.description}")
    print(f"Motivation: {goal.motivation}")
    print(f"Target date: {goal.target_date.isoformat() if goal.target_date else '(not set)'}")
    _print_items("Success criteria", goal.success_criteria)
    _print_items("Constraints", goal.constraints)

    print(f"\nRoute: {route.id} | {route.name}")
    print(f"Route status: {route.status}")
    print(f"Route content version: {route.version}")
    print(f"Route schema version: {route.schema_version}")
    print(f"Description: {route.description}")
    _print_items("Key hypotheses", route.key_hypotheses)
    _print_items("Focus dimensions (not score weights)", route.focus_dimensions)
    for label, signals in (("Specific signals", route.specific_signals), ("Costs", route.costs)):
        print(f"{label}:")
        if not signals:
            print("  (none configured)")
        for signal in signals:
            print(f"  {signal.id} | {signal.label}")
            print(f"    Match when: {signal.match_when}")
            print(f"    Configured daily_delta: {signal.daily_delta:+d}")

    calculation = route.calculation
    print("Calculation rules (configuration only; no scores calculated):")
    print(f"  formula_version: {calculation.formula_version}")
    print(f"  method: {calculation.method}")
    print(f"  daily_delta_range: {calculation.daily_delta_range}")
    print("  missing_value: null")


def run_route_command(args: argparse.Namespace) -> None:
    try:
        config = load_routes()
    except RouteConfigError as error:
        raise SystemExit(f"Route configuration error: {error}") from error

    if args.route_command == "list":
        list_routes(config)
    elif args.route_command == "show":
        show_route(config, args.route_id)

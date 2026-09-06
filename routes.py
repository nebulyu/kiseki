from pathlib import Path

import yaml
from pydantic import BaseModel, ValidationError

from route_schema import GoalsFile, RouteConfig, RouteDefinition


PROJECT_ROOT = Path(__file__).resolve().parent
GOALS_PATH = PROJECT_ROOT / "private" / "goals.yaml"
ROUTES_DIR = PROJECT_ROOT / "private" / "routes"


class RouteConfigError(ValueError):
    """A configuration file cannot be read or does not follow the route spec."""


def _load_file[T: BaseModel](path: Path, model: type[T]) -> T:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError) as error:
        raise RouteConfigError(f"{path}: could not read UTF-8 configuration: {error}") from error
    except (yaml.YAMLError, ValueError) as error:
        mark = getattr(error, "problem_mark", None)
        position = f" at line {mark.line + 1}, column {mark.column + 1}" if mark else ""
        problem = getattr(error, "problem", None) or str(error)
        raise RouteConfigError(f"{path}: YAML error{position}: {problem}") from error

    try:
        return model.model_validate(data)
    except ValidationError as error:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in item['loc']) or 'root'}: {item['msg']}"
            for item in error.errors(include_input=False, include_url=False)
        )
        raise RouteConfigError(f"{path}: {problems}") from error


def load_routes(
    goals_path: Path = GOALS_PATH,
    routes_dir: Path = ROUTES_DIR,
) -> RouteConfig:
    """Load and validate all definitions without accessing models or the diary DB."""
    goals_path = goals_path.resolve()
    routes_dir = routes_dir.resolve()
    if not goals_path.exists():
        raise RouteConfigError(
            f"{goals_path}: goals file not found. Create your goals.yaml using "
            "docs/templates/goal-definition.example.yaml as a format reference; "
            "see README for configuration steps. No files were created."
        )

    goals_file = _load_file(goals_path, GoalsFile)
    goals = {}
    for index, goal in enumerate(goals_file.goals):
        if goal.id in goals:
            raise RouteConfigError(
                f"{goals_path}: goals.{index}.id: duplicate goal ID '{goal.id}'."
            )
        goals[goal.id] = goal

    routes = {}
    sources = {}
    try:
        if not routes_dir.exists():
            return RouteConfig(goals=goals, routes=routes)
        if not routes_dir.is_dir():
            raise RouteConfigError(f"{routes_dir}: expected a routes directory.")
        route_files = sorted(
            path for path in routes_dir.iterdir() if path.suffix.lower() == ".yaml"
        )
    except OSError as error:
        raise RouteConfigError(f"{routes_dir}: could not list route files: {error}") from error

    for path in route_files:
        route = _load_file(path, RouteDefinition)
        if route.id in routes:
            raise RouteConfigError(
                f"{path}: id: duplicate route ID '{route.id}' "
                f"(also defined in {sources[route.id]})."
            )
        if route.goal_id not in goals:
            raise RouteConfigError(
                f"{path}: goal_id: unknown goal '{route.goal_id}' in {goals_path}."
            )
        routes[route.id] = route
        sources[route.id] = path

    return RouteConfig(goals=goals, routes=routes)

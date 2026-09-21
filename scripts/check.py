import os
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


def test_environment(environ: Mapping[str, str]) -> dict[str, str]:
    url = environ.get("TEST_DATABASE_URL", "")
    message = (
        "TEST_DATABASE_URL deve apontar para PostgreSQL exclusivo com nome terminado em _test."
    )
    try:
        parsed = make_url(url)
    except ArgumentError as error:
        raise SystemExit(message) from error
    if parsed.get_backend_name() != "postgresql" or not (parsed.database or "").endswith("_test"):
        raise SystemExit(message)
    # Alembic and application imports use DATABASE_URL, while fixtures use TEST_DATABASE_URL.
    return {**environ, "DATABASE_URL": url}


def main() -> None:
    environment = test_environment(os.environ)
    output_directory = Path(__file__).resolve().parents[1] / "evals" / "reports" / "local"
    commands = [
        ["ruff", "check", "src", "tests"],
        ["ruff", "format", "--check", "src", "tests"],
        ["mypy", "src"],
        ["alembic", "upgrade", "head"],
        [sys.executable, "-m", "pytest", "-q"],
        [sys.executable, "-m", "evals.runner", "--output-dir", str(output_directory)],
    ]
    for command in commands:
        print("\nExecutando:", " ".join(command), flush=True)
        subprocess.run(command, check=True, env=environment)


if __name__ == "__main__":
    main()

#!/usr/bin/env bash
# Run the pin gate, then lint, format, types and tests on Python 3.11 and 3.14.
# Each interpreter keeps its own environment (UV_PROJECT_ENVIRONMENT), so runs never
# replace .venv.
set -euo pipefail
cd "$(dirname "$0")/.."

uv run --no-project --python 3.11 -- python -I scripts/check_pins.py

for v in 3.11 3.14; do
  export UV_PROJECT_ENVIRONMENT=".venv-py${v}"
  uv sync --locked --python "$v"
  uv run --python "$v" ruff check .
  uv run --python "$v" ruff format --check .
  uv run --python "$v" pyright --pythonversion "$v" --pythonpath "${UV_PROJECT_ENVIRONMENT}/bin/python"
  if [ "$v" = "3.11" ]; then
    # Coverage gate: fail_under in pyproject.toml fails the run below 80 percent.
    timeout 300 uv run --python "$v" pytest -q --cov --cov-report=term-missing
  else
    timeout 300 uv run --python "$v" pytest -q
  fi
  echo "check: python ${v} ok"
done

echo "check: all ok"

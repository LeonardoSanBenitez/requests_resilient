#!/usr/bin/env bash
# This is intended to run from the project's base directory
# python3 -m pip install -e ".[dev]"

export PYTHONPATH=./src
mypy ./src
ruff check ./src ./tests
ruff format --check ./src ./tests
python3 -m unittest discover -s tests

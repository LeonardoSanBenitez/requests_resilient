#!/usr/bin/env bash
# This is intended to run from the project's base directory
# python3 -m pip install types-requests pycodestyle mypy

export PYTHONPATH=./src
mypy ./src
pycodestyle --max-line-length=190 --ignore='E121,E123,E126,E226,E24,E704,W503,W504,E225,E226,E252,W605,E731' ./src
python3 -m unittest discover -s tests

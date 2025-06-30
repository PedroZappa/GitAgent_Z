#!/usr/bin/env bash
# This script sets up a Python virtual environment and installs the necessary dependencies.

# Create virtual environment if it doesn't exist
if [ ! -d .venv ]; then
    python3 -m venv .venv
    echo ".venv created"
fi

# Always activate the virtual environment
source .venv/bin/activate

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -e .[dev]

pip list

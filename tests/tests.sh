#!/bin/bash
cd "$(dirname "$0")"

. ../venv/bin/pytest -q -s tests/test_login.py tests/test_api*.py

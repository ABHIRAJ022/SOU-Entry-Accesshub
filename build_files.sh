#!/usr/bin/env bash
set -euo pipefail

python3.10 -m pip install -r requirements.txt
python3.10 manage.py collectstatic --noinput
python3.10 manage.py migrate --noinput

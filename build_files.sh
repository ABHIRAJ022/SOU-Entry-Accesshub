#!/usr/bin/env bash
set -euo pipefail

python -m pip install -r requirements.txt
python manage.py collectstatic --noinput
cp -R staticfiles/. static/
python manage.py migrate --noinput

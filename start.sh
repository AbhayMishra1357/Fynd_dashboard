#!/usr/bin/env bash
set -e

# Activate virtual env not needed on Render; just run migrations
export FLASK_APP=manage.py

# run migrations (create tables). If migrations not initialized, this will error — run locally first.
flask db upgrade

# start gunicorn
exec gunicorn "app:create_app()" -b 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120

#!/usr/bin/env bash
set -e

: "${DJANGO_SETTINGS_MODULE:=firstproject.settings}"
: "${DJANGO_DEBUG:=0}"

mkdir -p /app/staticfiles /app/media

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static..."
python manage.py collectstatic --noinput

if [ "${RUNSERVER_PLUS:-0}" = "1" ]; then
  echo "Starting Django dev server..."
  exec python manage.py runserver 0.0.0.0:8000
else
  echo "Starting Gunicorn..."
  exec gunicorn firstproject.wsgi:application \
      --bind 0.0.0.0:8000 \
      --workers ${GUNICORN_WORKERS:-3} \
      --timeout ${GUNICORN_TIMEOUT:-60}
fi

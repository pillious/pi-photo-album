#!/bin/bash
set -euo pipefail

PYTHON_PATH=${1:-$(which python)}
echo $PYTHON_PATH

# handle app termination
cleanup() {
  echo "Stopping services..."

  echo "Killing slideshow"
  killall -15 fbi || true

  echo "Killing display_slideshow.sh"
  pkill -15 -f display_slideshow.sh || true

  if [[ -n "$EVENT_CONSUMER_PID" ]]; then
    echo "Killing event consumer (PID: $EVENT_CONSUMER_PID)"
    kill -TERM "$EVENT_CONSUMER_PID" || true
    wait "$EVENT_CONSUMER_PID" || true
  fi

  sleep 5
  if [[ -n "$API_PID" ]]; then
    echo "Killing API (PID: $API_PID)"
    kill -TERM "$API_PID" || true
    wait "$API_PID" || true
  fi

  echo "All services stopped." || true
  exit 0
}

# Trap signals
trap cleanup SIGINT SIGTERM

# start event consumer
echo "Starting event consumer service"
PYTHONPATH=/usr/local/bin/pi-photo-album "$PYTHON_PATH" -m app.event_consumer.main &
EVENT_CONSUMER_PID=$!

echo "sleep 5"
sleep 5

# start API
echo "Starting API"
PYTHONPATH=/usr/local/bin/pi-photo-album "$PYTHON_PATH" -m app.server &
API_PID=$!

wait
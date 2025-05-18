#!/bin/bash
set -euo pipefail

# handle app termination
cleanup() {
  echo "Stopping services..."
  echo "Killing slideshow"
  sudo killall -15 fbi
  if [[ -n "$EVENT_CONSUMER_PID" ]]; then
    echo "Killing event consumer (PID: $EVENT_CONSUMER_PID)"
    kill -TERM "$EVENT_CONSUMER_PID"
    wait "$EVENT_CONSUMER_PID"
  fi
  sleep 5   
  if [[ -n "$API_PID" ]]; then
    echo "Killing API (PID: $API_PID)"
    kill -TERM "$API_PID"
    wait "$API_PID"
  fi
  echo "All services stopped."
  exit 0
}

# Trap signals
trap cleanup SIGINT SIGTERM

# start event consumer
echo "Starting event consumer service"
python -m app.event_consumer.main &
EVENT_CONSUMER_PID=$!

echo "sleep 5"
sleep 5

# start API
echo "Starting API"
python -m app.server &
API_PID=$!

wait
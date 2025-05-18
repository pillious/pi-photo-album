#!/bin/bash
set -euo pipefail

album="$1"
speed="$2"
blend="$3"
randomize="$4"
image_order_file="$5"

slideshow_pid=
notifier_pid=

debounce_time=5
debounce_pid=

start_slideshow() {
    if [[ ! -d "$album" ]]; then
        echo "Album directory does not exist: $album"
        exit 1
    fi

    echo "Starting slideshow"
    # sudo fbi -d /dev/fb0 -T 1 -noverbose -readahead -a -t "$speed" -blend "$blend" -l "$image_order_file"
    # slideshow_pid=$!
}

kill_slideshow() {
    echo "Killing slideshow"
    if [[ -n "$slideshow_pid" ]] && kill -0 "$slideshow_pid" 2>/dev/null; then
        kill -15 "$slideshow_pid"
        wait "$slideshow_pid" 2>/dev/null || true
    fi
}

restart_slideshow() {
    kill_slideshow
    sleep 1
    start_slideshow
}

kill_debounce() {
  if [[ -n "$debounce_pid" ]] && kill -0 "$debounce_pid" 2>/dev/null; then
    kill "$debounce_pid"
    wait "$debounce_pid" 2>/dev/null || true
  fi
}

schedule_restart() {
  # Kill any existing pending restart timer
  kill_debounce

  # Start a new background timer to restart slideshow after debounce_time seconds
  (
    sleep "$debounce_time"
    restart_slideshow
  ) &
  debounce_pid=$!
}

cleanup() {
    echo "Cleaning up..."
    kill_debounce
    kill_slideshow
}

trap cleanup SIGINT SIGTERM

while read -r path file event; do
    full_path="$path$file"
    echo "$event: $full_path"

    # Update the $image_order_file based on the event
    if [[ "$event" == "CREATE" || "$event" == "MOVED_TO" ]]; then
        echo "$full_path" >> "$image_order_file"
    elif [[ "$event" == "DELETE" || "$event" == "MOVED_FROM" ]]; then
        sed -i "\|$file|d" "$image_order_file"
    elif [[ "$event" == "MODIFY" ]]; then
        : # noop
    else
        continue # Skip slideshow restarts for directory events
    fi

    # Schedule a restart of the slideshow
    schedule_restart
done < <(inotifywait -mre create,delete,modify,move --format '%w %f %e' "$album")

start_slideshow

#!/bin/bash
set -euxo pipefail

album="$1"
speed="$2"
blend="$3"
image_order_file="$4"

notifier_pid=
debounce_pid=

debounce_time=5

start_slideshow() {
    if [[ ! -d "$album" ]]; then
        echo "Album directory does not exist: $album"
        exit 1
    fi

    echo "Starting slideshow"
    fbi -d /dev/fb0 -T 1 -noverbose -readahead -a -t "$speed" -blend "$blend" -l "$image_order_file"
}

kill_slideshow() {
    echo "Killing slideshow"
    pkill -15 fbi || true
}

kill_notifier() {
    if [[ -n "$notifier_pid" ]] && kill -0 "$notifier_pid" 2>/dev/null; then
        kill -15 "$notifier_pid"
        wait "$notifier_pid" 2>/dev/null || true
    else
        echo "Failed to kill notifier with PID: $notifier_pid - Process not found or already terminated"
    fi
}

kill_debounce() {
    if [[ -n "$debounce_pid" ]] && kill -0 "$debounce_pid" 2>/dev/null; then
        kill "$debounce_pid"
        wait "$debounce_pid" 2>/dev/null || true
    fi
}

restart_slideshow() {
    kill_slideshow
    sleep 1
    start_slideshow
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

start_notifier() {
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
  done < <(inotifywait -mre create,delete,modify,move --format '%w %f %e' "$album") &
  notifier_pid=$!
}

cleanup() {
    echo "Cleaning up..."
    kill_debounce
    kill_slideshow
    kill_notifier
}

# When killed from python app, cleanup() doesn't get called.
trap cleanup SIGINT SIGTERM

start_slideshow
start_notifier

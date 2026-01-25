"""
Background worker that syncs pending events to cloud storage.
"""
import os
import json
import threading
import time

from app.config.config import config
from app.utils import pending, aws, filesystem
from app.cloud_clients.cloud_client import cloud_client


class EventPublisher:
    def __init__(self, interval: int = 10):
        self.interval = interval # seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self):
        """Start the background sync worker."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print("Event publisher started.")

    def stop(self):
        """Stop the background sync worker."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        print("Event publisher stopped.")

    def _run(self):
        """Main loop that processes pending events periodically."""
        while not self._stop_event.is_set():
            try:
                self._process_pending_events()
            except Exception as e:
                print(f"Event publisher error: {e}")
            self._stop_event.wait(self.interval)

    def trigger(self):
        """Trigger an immediate sync attempt in a separate thread."""
        threading.Thread(target=self._process_pending_events, daemon=True).start()

    def _process_pending_events(self):
        """Process pending events from the pending events file."""
        s3_ping_url = config()['url']['s3_ping_url'].as_str()
        pending_events_file = config()['paths']['pending_events_file'].as_str()

        # Check if we're online
        if not aws.ping(s3_ping_url):
            return

        # Read pending events from file
        events = pending.get_pending_events(pending_events_file)
        if not events:
            return

        print(f"Processing {len(events)} pending events...")

        # Group events by type for bulk operations
        put_events = [e for e in events if e['event'] == 'PUT']
        delete_events = [e for e in events if e['event'] == 'DELETE']
        move_events = [e for e in events if e['event'] == 'MOVE']

        queue_events = []       # Events to broadcast to other clients
        successful_keys = set() # Track successful event keys for removal

        # Process PUT events (uploads)
        if put_events:
            paths = [e['path'] for e in put_events]
            abs_paths = [filesystem.key_to_abs_path(p) for p in paths]

            # Filter out files that no longer exist (deleted after queuing)
            valid_pairs = [(abs_p, p) for abs_p, p in zip(abs_paths, paths)
                          if os.path.exists(abs_p)]
            skipped_paths = {p for abs_p, p in zip(abs_paths, paths)
                            if not os.path.exists(abs_p)}

            if valid_pairs:
                abs_paths, paths = zip(*valid_pairs)
                success, failure = cloud_client().insert_bulk(list(abs_paths), list(paths))
                success_set = set(success)

                # Track successes for removal from queue
                for e in put_events:
                    if e['path'] in success_set or e['path'] in skipped_paths:
                        successful_keys.add((e['timestamp'], e['event'], e['path']))

                queue_events.extend([{"event": "PUT", "path": p} for p in success])

                if failure:
                    print(f"Failed to upload (will retry): {failure}")
            else:
                # All files were skipped (deleted), mark as successful
                for e in put_events:
                    successful_keys.add((e['timestamp'], e['event'], e['path']))

        # Process DELETE events
        if delete_events:
            paths = [e['path'] for e in delete_events]
            success, failure = cloud_client().delete_bulk(paths)
            success_set = set(success)

            for e in delete_events:
                if e['path'] in success_set:
                    successful_keys.add((e['timestamp'], e['event'], e['path']))

            queue_events.extend([{"event": "DELETE", "path": p} for p in success])

            if failure:
                print(f"Failed to delete (will retry): {failure}")

        # Process MOVE events
        if move_events:
            pairs = [(e['path'], e['newPath']) for e in move_events]
            success, failure = cloud_client().move_bulk(pairs)

            success_old_paths = {p[0] for p in success}
            for e in move_events:
                if e['path'] in success_old_paths:
                    successful_keys.add((e['timestamp'], e['event'], e['path']))

            queue_events.extend([{"event": "MOVE", "path": p[0], "newPath": p[1]}
                               for p in success])

            if failure:
                print(f"Failed to move (will retry): {failure}")

        # Broadcast successful events to other clients via SQS
        if queue_events:
            message = json.dumps({
                "events": queue_events,
                "sender": os.getenv('USERNAME')
            })
            cloud_client().insert_queue(message)

        # Update queue file - clear and re-save failed events for retry
        failed_events = [e for e in events
                         if (e['timestamp'], e['event'], e['path']) not in successful_keys]

        pending.clear_pending_events(pending_events_file)
        if failed_events:
            retry_events = [
                pending.create_pending_event(e['event'], e['path'], e.get('newPath', ''))
                for e in failed_events
            ]
            pending.save_pending_events(pending_events_file, retry_events)
            print(f"Synced {len(successful_keys)} events. {len(failed_events)} pending retry.")
        else:
            print(f"Synced {len(successful_keys)} events.")


# Global singleton
_event_publisher: EventPublisher | None = None

def init_event_publisher(interval: int = 10):
    global _event_publisher
    if _event_publisher is not None:
        return  # Already initialized
    _event_publisher = EventPublisher(interval)
    _event_publisher.start()

def event_publisher() -> EventPublisher:
    if _event_publisher is None:
        raise RuntimeError("Event publisher not initialized. Call init_event_publisher() first.")
    return _event_publisher


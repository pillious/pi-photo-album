import queue

class EventAnnouncer:
    def __init__(self):
        self.subscribers: list[queue.Queue[str]] = []

    def subscribe(self, queue_size = 10):
        q = queue.Queue(queue_size)
        self.subscribers.append(q)
        # With JS EventSource, need to send a message on connection request to complete the connection. 
        q.put_nowait(self.format_sse("connected"))
        return q
    
    def announce(self, event: str):
        for i in reversed(range(len(self.subscribers))):
            try:
                self.subscribers[i].put_nowait(self.format_sse(event))
            except queue.Full:
                del self.subscribers[i]

    def format_sse(self, data: str, event="") -> str:
        msg = f'data: {data}\n\n'
        if event:
            msg = f'event: {event}\n{msg}'
        return msg

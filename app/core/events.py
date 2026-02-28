import asyncio
import threading

_lock = threading.Lock()
clients: set = set()
main_loop: asyncio.AbstractEventLoop | None = None


def notify_clients(message: str):
    with _lock:
        loop = main_loop
        client_list = list(clients)
    if loop:
        for q in client_list:
            loop.call_soon_threadsafe(q.put_nowait, message)


def add_client(q: asyncio.Queue):
    with _lock:
        clients.add(q)


def remove_client(q: asyncio.Queue):
    with _lock:
        clients.discard(q)


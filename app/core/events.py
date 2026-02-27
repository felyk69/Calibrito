import asyncio

clients = set()
main_loop = None

def notify_clients(message: str):
    if main_loop:
        for q in list(clients):
            main_loop.call_soon_threadsafe(q.put_nowait, message)

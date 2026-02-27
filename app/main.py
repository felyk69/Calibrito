import asyncio
import threading
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from app.core.database import init_db
from app.services.book_service import scan_books
from app.services.watchdog_service import start_watchdog, stop_watchdog
from app.core import events
from app.api.routes import books, metadata, events as events_route, misc

app = FastAPI(title="Kindle Library Manager")
templates = Jinja2Templates(directory="templates")

app.mount("/covers", StaticFiles(directory="covers"), name="covers")

app.include_router(books.router)
app.include_router(metadata.router)
app.include_router(events_route.router)
app.include_router(misc.router)

@app.on_event("startup")
def startup():
    try:
        events.main_loop = asyncio.get_running_loop()
    except Exception:
        pass
    
    init_db()
    
    def run_scanner():
        print("[Scanner] Iniciando varredura da biblioteca em segundo plano...", flush=True)
        scan_books()
        print("[Scanner] Varredura concluída!", flush=True)
        
    threading.Thread(target=run_scanner, daemon=True).start()
    start_watchdog()

@app.on_event("shutdown")
def shutdown():
    stop_watchdog()
    print("[Watchdog] Observer encerrado.", flush=True)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

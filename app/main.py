import asyncio
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from app.core.database import init_db
from app.core.logger import setup_logging, get_logger
from app.services.book_service import scan_books
from app.services.watchdog_service import start_watchdog, stop_watchdog
from app.core import events
from app.api.routes import books, metadata, events as events_route, misc

setup_logging()
logger = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    events.main_loop = asyncio.get_running_loop()
    init_db()

    def run_scanner():
        logger.info("Starting library scan in background...")
        scan_books()
        logger.info("Library scan completed.")

    threading.Thread(target=run_scanner, daemon=True).start()
    start_watchdog()

    yield

    # --- Shutdown ---
    stop_watchdog()
    logger.info("Watchdog observer stopped.")


app = FastAPI(title="Kindle Library Manager", lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

app.mount("/covers", StaticFiles(directory="covers"), name="covers")
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(books.router)
app.include_router(metadata.router)
app.include_router(events_route.router)
app.include_router(misc.router)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/reader", response_class=HTMLResponse)
async def reader(request: Request):
    return templates.TemplateResponse("reader.html", {"request": request})

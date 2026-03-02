import asyncio
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.api.routes import books, metadata, misc
from app.api.routes import events as events_route
from app.core import events
from app.core.database import init_db
from app.core.logger import get_logger, setup_logging
from app.services.book_service import scan_books
from app.services.watchdog_service import start_watchdog, stop_watchdog

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


limiter = Limiter(key_func=get_remote_address, default_limits=["500/minute"])

app = FastAPI(title="Kindle Library Manager", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

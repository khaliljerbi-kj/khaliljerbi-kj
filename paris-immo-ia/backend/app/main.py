import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import alerts, chat, meta, transcribe
from .workers.alerts import periodic

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    interval = get_settings().alerts_interval_seconds
    task = asyncio.create_task(periodic(interval)) if interval > 0 else None
    yield
    if task:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="Paris Immo IA", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in get_settings().cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)
for module in (chat, transcribe, alerts, meta):
    app.include_router(module.router)

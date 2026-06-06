"""Application FastAPI NettoyerGmail."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import cache
from .routers import auth, groups, emails, actions

load_dotenv()

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(os.getenv("DB_PATH", "/data/gmail_cache.db")).parent.mkdir(parents=True, exist_ok=True)
    cache.init_db()
    yield


app = FastAPI(title="NettoyerGmail", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:5173", "http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(groups.router)
app.include_router(emails.router)
app.include_router(actions.router)


@app.get("/health")
def health():
    return {"status": "ok"}

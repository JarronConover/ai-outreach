"""
Backend entry point.

Start with:
    uvicorn backend.main:app --reload
"""
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from backend.routers import (  # noqa: E402 — load_dotenv must run first
    dashboard,
    people,
    companies,
    demos,
    emails,
    actions,
    orchestrator,
    imports,
    add,
    references,
)
from backend.services.poller import seed_seen_ids, start_background_threads, stop_background_threads  # noqa: E402
from backend.auth import AuthMiddleware  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_seen_ids()
    start_background_threads()
    yield
    stop_background_threads()


app = FastAPI(title="AI Outreach API", version="0.1.0", lifespan=lifespan)

app.add_middleware(AuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Mount all routers
app.include_router(dashboard.router)
app.include_router(people.router)
app.include_router(companies.router)
app.include_router(demos.router)
app.include_router(emails.router)
app.include_router(actions.router)
app.include_router(orchestrator.router)
app.include_router(imports.router)
app.include_router(add.router)
app.include_router(references.router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}

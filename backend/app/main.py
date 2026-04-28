from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, devices, jobs, reservations, users, ws
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.init_db import init_db
    await init_db()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
    root_path="/api",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["auth"])
app.include_router(users.router, prefix=f"{settings.API_V1_PREFIX}/users", tags=["users"])
app.include_router(devices.router, prefix=f"{settings.API_V1_PREFIX}/devices", tags=["devices"])
app.include_router(reservations.router, prefix=f"{settings.API_V1_PREFIX}/reservations", tags=["reservations"])
app.include_router(jobs.router, prefix=f"{settings.API_V1_PREFIX}/jobs", tags=["jobs"])
app.include_router(ws.router)


@app.get("/health")
async def health():
    return {"status": "ok"}

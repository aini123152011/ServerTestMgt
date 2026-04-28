from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, devices, jobs, reservations, users, ws
from app.api import firmware, fru, provision, ras, reports, cicd, api_keys
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
app.include_router(provision.router, prefix=f"{settings.API_V1_PREFIX}/provision", tags=["provision"])
app.include_router(firmware.router, prefix=f"{settings.API_V1_PREFIX}/firmware", tags=["firmware"])
app.include_router(fru.router, prefix=f"{settings.API_V1_PREFIX}/fru", tags=["fru"])
app.include_router(ras.router, prefix=f"{settings.API_V1_PREFIX}/ras", tags=["ras"])
app.include_router(reports.router, prefix=f"{settings.API_V1_PREFIX}/reports", tags=["reports"])
app.include_router(cicd.router, prefix=f"{settings.API_V1_PREFIX}/cicd", tags=["cicd"])
app.include_router(api_keys.router, prefix=f"{settings.API_V1_PREFIX}/api-keys", tags=["api-keys"])
app.include_router(ws.router)


@app.get("/health")
async def health():
    return {"status": "ok"}

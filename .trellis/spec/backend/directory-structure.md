# Directory Structure

> How backend code is organized in this project.

---

## Overview

The backend is a FastAPI application using async SQLAlchemy, Celery for task execution, and a hardware driver abstraction layer for BMC (IPMI/Redfish) operations.

---

## Directory Layout

```
backend/
├── app/
│   ├── main.py              # FastAPI app entry, router registration, lifespan
│   ├── init_db.py           # Auto-create tables + seed admin user on startup
│   ├── api/                 # FastAPI route modules (one file per domain)
│   │   ├── deps.py          # Shared dependencies: get_current_user, require_role
│   │   ├── auth.py          # Login, register, /me
│   │   ├── users.py         # User CRUD (admin only)
│   │   ├── devices.py       # Device CRUD, power control, state transitions
│   │   ├── reservations.py  # Device reservation/locking
│   │   ├── jobs.py          # Test job CRUD, cancel, logs
│   │   ├── ws.py            # WebSocket endpoint for real-time job streaming
│   │   ├── provision.py     # PXE provisioning + callback
│   │   ├── firmware.py      # Firmware upgrade (single + batch)
│   │   ├── fru.py           # FRU read/write/batch-write
│   │   ├── ras.py           # RAS error injection + verification
│   │   ├── reports.py       # Report generation + export (JSON/CSV/HTML)
│   │   ├── cicd.py          # CI/CD trigger + status (API key auth)
│   │   └── api_keys.py      # API key management
│   ├── core/                # Framework-level infrastructure
│   │   ├── config.py        # Pydantic BaseSettings (env-driven)
│   │   ├── database.py      # Async SQLAlchemy engine + session factory
│   │   ├── security.py      # JWT encode/decode, password hashing
│   │   └── websocket.py     # WebSocket manager + Redis pub/sub relay
│   ├── models/              # SQLAlchemy ORM models
│   │   ├── base.py          # DeclarativeBase, IDMixin, TimestampMixin
│   │   ├── user.py          # User + UserRole enum
│   │   ├── device.py        # Device + DeviceState state machine + BmcProtocol
│   │   ├── reservation.py   # Reservation + ReservationStatus
│   │   ├── job.py           # TestJob + TestJobLog + enums
│   │   ├── provision.py     # ProvisionJob + ProvisionStatus
│   │   ├── firmware.py      # FirmwareJob + FirmwareJobStatus
│   │   └── api_key.py       # APIKey (hashed storage)
│   ├── schemas/             # Pydantic request/response models
│   │   ├── common.py        # PageParams, PageResult[T], MessageResponse, TimestampSchema
│   │   └── <domain>.py      # One file per domain matching api/ modules
│   ├── services/            # Business logic (stateless service classes)
│   │   ├── test_pipeline.py # LAVA-inspired deploy→boot→test→collect→cleanup
│   │   ├── pxe_service.py   # dnsmasq config + kickstart generation (Jinja2)
│   │   ├── provision_service.py # PXE provisioning orchestration
│   │   ├── firmware_service.py  # Firmware upgrade orchestration
│   │   ├── ras_service.py   # EINJ error injection + verification
│   │   └── report_service.py # Report generation + export
│   ├── drivers/             # Hardware abstraction layer (BMC protocols)
│   │   ├── base.py          # ABC interfaces: Power, Management, Console, Firmware, FRU, Inspect
│   │   ├── ipmi.py          # IPMI implementation (pyghmi + ipmitool fallback)
│   │   ├── redfish.py       # Redfish implementation (python-redfish-library)
│   │   └── factory.py       # get_driver(protocol, host, user, pass) factory
│   └── workers/             # Celery task modules
│       ├── celery_app.py    # Celery app config (long-task tuned)
│       ├── test_tasks.py    # Test execution tasks (stress/stability/performance)
│       ├── bmc_tasks.py     # Background BMC tasks (sensors, health check)
│       └── webhook_tasks.py # CI/CD webhook callback tasks
├── alembic/                 # Database migrations
├── tests/
└── pyproject.toml
```

---

## Module Organization

New features follow this pattern:
1. **Model** in `models/<domain>.py` — extend `Base, IDMixin, TimestampMixin`
2. **Schema** in `schemas/<domain>.py` — Pydantic models, use `TimestampSchema` for reads
3. **Service** in `services/<domain>_service.py` (if business logic is non-trivial)
4. **API** in `api/<domain>.py` — FastAPI router, use deps from `api/deps.py`
5. **Worker** in `workers/<domain>_tasks.py` (if async/background work needed)
6. **Register** router in `main.py`, model import in `alembic/env.py` and `init_db.py`

---

## Naming Conventions

- Files: `snake_case.py`
- Models: `PascalCase` (e.g., `TestJob`, `FirmwareJob`)
- Enums: `PascalCase` with `str, enum.Enum` mixin for JSON serialization
- API routes: plural nouns (`/devices/`, `/jobs/`, `/reservations/`)
- Celery tasks: `module.function_name` (e.g., `app.workers.test_tasks.run_test`)

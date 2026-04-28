# Research: Tech Stack for BMC Server Test Platform

- **Query**: Best tech stack for BMC server test platform (backend, frontend, task queue, database, real-time)
- **Scope**: external
- **Date**: 2026-04-28

---

## 1. Python Backend Framework

### Comparison

| Criteria | FastAPI | Django | Flask |
|---|---|---|---|
| Async native | Yes (ASGI, built on Starlette) | Partial (Django 4.1+ async views, but ORM is sync) | No (requires extensions like Quart) |
| API-first design | Yes (auto OpenAPI/Swagger docs) | No (DRF adds it, but heavier) | No (Flask-RESTX/Marshmallow needed) |
| WebSocket support | Native (via Starlette) | Channels (separate package) | Flask-SocketIO (separate) |
| Learning curve | Low-medium | High (large framework) | Low |
| Built-in admin | No | Yes (powerful) | No |
| ORM included | No (pairs with SQLAlchemy/Tortoise) | Yes (Django ORM) | No |
| Type safety | Excellent (Pydantic models) | Moderate | Weak |
| Performance | High (async I/O) | Moderate | Moderate |
| Maturity | Production-ready since ~2020 | Very mature (15+ years) | Very mature |

### Recommendation: FastAPI

**Why FastAPI wins for this use case:**

1. **Async-native matters here.** The platform will manage long-running test jobs across many servers. FastAPI's native async support means the API layer can handle hundreds of concurrent status-polling connections without blocking threads. Django's async story is still incomplete — the ORM remains synchronous, which creates awkward patterns when you need async views + DB access.

2. **WebSocket support is built-in.** Live test status updates are a core requirement. FastAPI/Starlette handles WebSocket endpoints as first-class citizens. Django requires the Channels package (adds Redis dependency and ASGI complexity).

3. **Pydantic models = self-documenting API.** Test configurations, device inventories, and job definitions are complex nested structures. Pydantic gives you validation, serialization, and auto-generated OpenAPI docs for free. This is huge for an internal tool where the API will be consumed by scripts and automation.

4. **Lighter weight than Django.** This is a task orchestration platform, not a content management system. Django's admin panel is nice but not essential — a custom frontend is already planned. The batteries Django includes (auth, admin, forms, templates) are mostly irrelevant here.

5. **SQLAlchemy pairing is powerful.** SQLAlchemy 2.0+ with async support (via asyncpg) gives more control over complex queries than Django ORM, especially for reporting/analytics on test results.

**When Django would be better:** If the team had strong Django experience and wanted rapid prototyping with the admin panel as a quick management UI. But for a purpose-built test platform, FastAPI's architecture is a better fit.

**Flask is not recommended** because it lacks async support natively and would require too many extensions to match what FastAPI provides out of the box.

### Suggested FastAPI Stack

```
FastAPI + Uvicorn (ASGI server)
SQLAlchemy 2.0+ (async mode with asyncpg)
Pydantic v2 (data validation/serialization)
Alembic (database migrations)
```

---

## 2. Task Queue / Job Scheduler

### Comparison

| Criteria | Celery | Dramatiq | RQ (Redis Queue) | Huey |
|---|---|---|---|---|
| Maturity | Very mature, industry standard | Mature, modern design | Mature, simple | Lightweight |
| Broker support | Redis, RabbitMQ, SQS | Redis, RabbitMQ | Redis only | Redis, SQLite |
| Long-running tasks | Yes (with `acks_late`, visibility timeout tuning) | Yes (better defaults for long tasks) | Limited (no native timeout extension) | Limited |
| Task chaining/workflows | Yes (canvas: chain, group, chord) | Yes (pipelines, groups) | No | Basic |
| Monitoring | Flower (web UI) | No built-in (Prometheus exportable) | rq-dashboard | Basic |
| Retry/backoff | Yes (configurable) | Yes (built-in, cleaner API) | Basic | Basic |
| Priority queues | Yes | Yes | Yes | Yes |
| Rate limiting | Yes | Yes (per-actor) | No | No |
| Periodic tasks | Celery Beat | APScheduler integration | rq-scheduler | Built-in |
| Complexity | High (many config options) | Medium | Low | Low |
| Community/ecosystem | Largest | Growing | Medium | Small |

### Recommendation: Celery (primary) or Dramatiq (alternative)

**Why Celery for this use case:**

1. **Battle-tested for long-running jobs.** BMC tests can run hours or days. Celery with `acks_late=True` and proper visibility timeout configuration handles this well. Workers can be configured to not prefetch tasks, ensuring long jobs don't starve the queue.

2. **Canvas workflows are essential.** Test execution often follows patterns like: provision server -> run pre-checks -> execute test suite -> collect results -> cleanup. Celery's `chain`, `group`, and `chord` primitives model this naturally.

3. **Flower provides monitoring out of the box.** For an internal tool, having a web dashboard showing active workers, task progress, and failure rates is valuable without building custom UI.

4. **Celery Beat for scheduled/recurring tests.** Nightly regression suites, periodic health checks — Celery Beat handles cron-like scheduling natively.

5. **Scalability.** Can scale workers horizontally across machines. Different queues for different test types (quick smoke tests vs. multi-day stress tests).

**Celery configuration tips for long-running tasks:**

```python
# celery_config.py
task_acks_late = True
task_reject_on_worker_lost = True
worker_prefetch_multiplier = 1
task_soft_time_limit = 86400      # 24 hours soft limit
task_time_limit = 90000           # 25 hours hard limit
result_expires = 604800           # Results kept for 7 days
broker_transport_options = {
    'visibility_timeout': 90000   # Must exceed task_time_limit
}
```

**When to consider Dramatiq instead:**
- If the team finds Celery's configuration complexity frustrating
- Dramatiq has saner defaults for long-running tasks (no visibility timeout issues)
- Cleaner, more Pythonic API
- But smaller ecosystem and no built-in monitoring UI

**RQ and Huey are not recommended** — they lack the workflow primitives and robustness needed for complex, long-running test orchestration.

### Broker choice: Redis vs RabbitMQ

| Criteria | Redis | RabbitMQ |
|---|---|---|
| Simplicity | Simpler to deploy/manage | More complex |
| Persistence | Optional (RDB/AOF) | Built-in durable queues |
| Message guarantees | At-most-once (default) | At-least-once |
| Performance | Very fast | Fast |
| Also useful for | Caching, pub/sub, session store | Only messaging |

**Recommendation: Redis** — simpler to operate, and it doubles as the caching layer and WebSocket pub/sub backend. For an internal tool, Redis's message guarantees are sufficient. If message loss during Redis restart is unacceptable, enable AOF persistence.

---

## 3. Frontend Framework

### Comparison

| Criteria | React | Vue 3 | Server-side templates (Jinja2) |
|---|---|---|---|
| Interactivity | Full SPA | Full SPA | Limited (requires JS sprinkles) |
| Real-time updates | Excellent (React Query + WebSocket) | Excellent (composables + WebSocket) | Poor (needs full page reload or HTMX) |
| Learning curve | Medium-high (JSX, hooks, ecosystem choices) | Low-medium (SFC, Composition API) | Low |
| Component ecosystem | Massive (MUI, Ant Design, shadcn/ui) | Large (Element Plus, Naive UI, PrimeVue) | N/A |
| TypeScript support | Excellent | Excellent | N/A |
| Build tooling | Vite / Next.js | Vite (native) | None needed |
| Table/data grid | AG Grid, TanStack Table | AG Grid, VxeTable | Basic HTML tables |
| Chart/visualization | Recharts, ECharts | ECharts, Chart.js | Server-rendered images |

### Recommendation: Vue 3 + Vite

**Why Vue 3 for this use case:**

1. **Lower barrier for backend-heavy teams.** Hardware test teams are typically stronger in Python/scripting than frontend. Vue's Single File Components (SFC) with `<template>`, `<script>`, `<style>` in one file are more intuitive than React's JSX-everything approach.

2. **Composition API is powerful enough.** Vue 3's Composition API handles complex state (test job trees, device inventories, real-time status) cleanly without the ecosystem decision paralysis of React (Redux vs Zustand vs Jotai vs...).

3. **Real-time updates work well.** Vue's reactivity system + composables make WebSocket integration straightforward. A `useTestStatus(jobId)` composable that auto-updates from WebSocket is clean and reusable.

4. **Good data table options.** Test platforms are table-heavy (device lists, test results, job queues). VxeTable or AG Grid with Vue bindings handle large datasets with sorting, filtering, and virtual scrolling.

5. **Vite is Vue-native.** Zero-config dev server with HMR. No webpack configuration headaches.

**Suggested Vue stack:**

```
Vue 3 + Composition API + TypeScript
Vite (build tool)
Pinia (state management)
Vue Router (routing)
Element Plus or Naive UI (component library)
ECharts (test metrics visualization)
VxeTable (data grids for test results/device inventory)
```

**When React would be better:** If the team already has React experience, or if hiring frontend developers is planned (React has a larger talent pool). But for an internal tool built primarily by backend engineers, Vue's gentler learning curve wins.

**Server-side templates are not recommended** because real-time test monitoring with live status updates requires significant client-side interactivity that templates handle poorly.

---

## 4. Database

### Primary Database: PostgreSQL

| Criteria | PostgreSQL | MySQL |
|---|---|---|
| JSON support | Excellent (JSONB with indexing) | JSON type (no indexing on expressions) |
| Array columns | Native | No |
| Full-text search | Built-in (ts_vector) | Built-in (less flexible) |
| Partitioning | Declarative (PG 10+) | Range/list/hash |
| Extensions | Rich (pg_cron, pg_stat, TimescaleDB) | Limited |
| Concurrent writes | MVCC, excellent | Good with InnoDB |
| Complex queries | Superior optimizer | Good |
| SQLAlchemy support | Excellent (asyncpg driver) | Good (aiomysql driver) |

**Why PostgreSQL:**

1. **JSONB for flexible test configurations.** BMC test configs vary wildly between test types. JSONB columns with GIN indexes let you store semi-structured config data without schema migrations for every new test parameter.

2. **Table partitioning for test results.** Test results accumulate fast. PostgreSQL's declarative partitioning (by date range) keeps queries fast and makes archival/cleanup straightforward.

3. **TimescaleDB extension for time-series metrics.** If you need to store continuous test metrics (temperatures, power readings, error rates over time), TimescaleDB turns PostgreSQL into a time-series database without adding a separate system.

4. **Array columns for tags/labels.** Devices and tests often have multiple tags. PostgreSQL's native array type with GIN indexing is cleaner than a separate tags junction table.

### Schema Design Considerations

```
Core tables:
- devices          (server inventory, BMC connection info, status)
- test_definitions (test templates, parameters schema)
- test_configs     (specific test configurations, JSONB params)
- test_jobs        (scheduled/running/completed test executions)
- test_results     (per-job results, pass/fail, logs reference)
- test_metrics     (time-series data if using TimescaleDB)
- users            (team members, permissions)
- job_logs         (structured log entries per job)
```

### Time-Series Data Decision

Two viable approaches:

**Option A: TimescaleDB extension (recommended for simplicity)**
- Install as PostgreSQL extension, no separate service
- Hypertables for metrics data with automatic partitioning
- Compression for old data (10-20x reduction)
- Continuous aggregates for dashboards
- Single database to manage

**Option B: Separate time-series DB (InfluxDB/Prometheus)**
- Better for very high-frequency metrics (>1M points/sec)
- More operational complexity (two databases)
- Only justified if metrics volume is extreme

For a BMC test platform, Option A (TimescaleDB) is almost certainly sufficient. Test metrics are typically sampled at seconds-to-minutes intervals, not milliseconds.

---

## 5. Real-Time Communication

### WebSocket Architecture

**Recommended: FastAPI WebSocket + Redis Pub/Sub**

```
[Browser] <--WebSocket--> [FastAPI] <--Pub/Sub--> [Redis] <--Publish--> [Celery Worker]
```

**How it works:**

1. Celery workers publish test status updates to Redis channels (e.g., `test:job:{job_id}:status`)
2. FastAPI WebSocket endpoints subscribe to relevant Redis channels
3. Browser connects via WebSocket, receives real-time updates
4. When WebSocket disconnects, subscription is cleaned up

**Why this approach:**

- Redis is already in the stack (Celery broker + cache)
- No additional infrastructure needed
- Scales horizontally — multiple FastAPI instances can subscribe to the same Redis channels
- Simple pub/sub pattern, no complex message routing

**Alternative considered: Server-Sent Events (SSE)**
- Simpler than WebSocket (HTTP-based, auto-reconnect)
- One-directional (server -> client only)
- Sufficient if the client never needs to send messages to the server via the real-time channel
- Could be used for simple status feeds, with WebSocket reserved for interactive features

**Suggested approach:** Use WebSocket for the primary real-time channel (supports bidirectional communication for future features like remote test control), with SSE as a fallback for simpler monitoring views.

---

## 6. Complete Recommended Stack

### Backend
| Component | Technology | Purpose |
|---|---|---|
| Framework | FastAPI + Uvicorn | API server, WebSocket |
| ORM | SQLAlchemy 2.0 (async) | Database access |
| Migrations | Alembic | Schema migrations |
| Validation | Pydantic v2 | Request/response models |
| Auth | FastAPI security + JWT | Internal auth |

### Task Queue
| Component | Technology | Purpose |
|---|---|---|
| Queue | Celery 5.x | Task orchestration |
| Broker | Redis 7.x | Message broker + cache + pub/sub |
| Scheduler | Celery Beat | Periodic test scheduling |
| Monitor | Flower | Worker/task monitoring |

### Frontend
| Component | Technology | Purpose |
|---|---|---|
| Framework | Vue 3 + TypeScript | UI framework |
| Build | Vite | Dev server + bundler |
| State | Pinia | State management |
| UI Library | Element Plus or Naive UI | Component library |
| Charts | ECharts | Test metrics visualization |
| Tables | VxeTable | Data grids |
| Real-time | Native WebSocket API | Live updates |

### Database & Storage
| Component | Technology | Purpose |
|---|---|---|
| Primary DB | PostgreSQL 16+ | Main data store |
| Time-series | TimescaleDB (PG extension) | Test metrics |
| Cache | Redis 7.x | Caching, sessions |
| File storage | Local filesystem or MinIO | Test logs, artifacts |

### Infrastructure
| Component | Technology | Purpose |
|---|---|---|
| Containerization | Docker + Docker Compose | Local dev + deployment |
| Reverse proxy | Nginx or Traefik | SSL, routing, static files |
| Process manager | Supervisor or systemd | Worker management |
| Logging | Structured JSON logs + ELK or Loki | Centralized logging |

---

## 7. Caveats / Risks

1. **Celery long-task visibility timeout** is a known pain point. Must be configured carefully or tasks will be re-delivered to other workers while still running. Dramatiq avoids this issue by design.

2. **SQLAlchemy async mode** is mature but has some gotchas with lazy loading (not supported in async). Relationships must use `selectinload` or `joinedload` explicitly.

3. **TimescaleDB** adds a PostgreSQL extension dependency. If deployment constraints prevent extensions, fall back to partitioned regular tables with manual aggregation.

4. **Vue ecosystem** is smaller than React's in the English-speaking world, but has excellent Chinese-language resources and component libraries (Element Plus, Naive UI are both Chinese-origin projects with good English docs). This could be an advantage given the team context.

5. **Redis as single point of failure** — it serves as broker, cache, and pub/sub. Consider Redis Sentinel or a small Redis Cluster for production reliability.

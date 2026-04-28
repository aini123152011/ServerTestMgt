# Backend Development Guidelines

> Best practices for backend development in this project.

---

## Overview

This is a FastAPI + SQLAlchemy 2.0 (async) + Celery backend for a BMC server test platform. It manages 1000+ devices via IPMI/Redfish, orchestrates test execution, and provides REST APIs + WebSocket for real-time monitoring.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | Module organization and file layout | ✅ Filled |
| [Database Guidelines](./database-guidelines.md) | ORM patterns, queries, migrations | ✅ Filled |
| [Error Handling](./error-handling.md) | Error types, handling strategies | ✅ Filled |
| [Quality Guidelines](./quality-guidelines.md) | Code standards, forbidden patterns | ✅ Filled |
| [Logging Guidelines](./logging-guidelines.md) | Structured logging, log levels | To fill |

---

## Key Architecture Decisions

### Hardware Driver Abstraction (Ironic-inspired)
Six interfaces (Power, Management, Console, Firmware, FRU, Inspect) with IPMI and Redfish implementations. Use `drivers/factory.py` to get the right driver by protocol.

### Test Pipeline (LAVA-inspired)
deploy → boot → test → collect → cleanup stages. Each test type (stress/stability/performance) subclasses the base pipeline.

### Device State Machine
`New → Commissioning → Ready → Reserved → Deploying → Testing → Ready` with maintenance and offline escape paths. Transitions validated by `device.can_transition_to()`.

### Dual Auth: JWT + API Key
Web UI uses JWT (OAuth2 bearer). CI/CD uses API key (X-API-Key header). Both resolve to a User for RBAC.

---

**Language**: All documentation should be written in **English**.

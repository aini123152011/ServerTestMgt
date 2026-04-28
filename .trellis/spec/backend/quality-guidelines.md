# Quality Guidelines

> Code quality standards for backend development.

---

## Overview

- **Linter**: ruff (target Python 3.11, line-length 120)
- **Type checker**: mypy (strict mode recommended)
- **Test framework**: pytest + pytest-asyncio
- **Async mode**: `asyncio_mode = "auto"` in pytest config

---

## Forbidden Patterns

### Sync DB access in FastAPI endpoints
```python
# WRONG — blocks the event loop
session.query(Device).filter_by(id=1).first()

# CORRECT
result = await db.execute(select(Device).where(Device.id == 1))
device = result.scalar_one_or_none()
```

### Lazy loading in async context
```python
# WRONG — raises MissingGreenlet error
device.reservations  # implicit lazy load

# CORRECT — use eager loading
select(Device).options(selectinload(Device.reservations))
# or define relationship with lazy="selectin"
```

### Hardcoded credentials or secrets
All secrets must come from environment variables via `core/config.py` Settings.

### Direct subprocess calls without timeout
```python
# WRONG
subprocess.run(cmd.split())

# CORRECT
subprocess.run(cmd.split(), capture_output=True, text=True, timeout=30)
```

---

## Required Patterns

### All new models must use base mixins
```python
class MyModel(Base, IDMixin, TimestampMixin):
    __tablename__ = "my_models"
```

### All API endpoints must use dependency injection for auth
```python
@router.get("/")
async def list_items(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),  # or require_role(...)
):
```

### All new routers must be registered in main.py
And all new models imported in `alembic/env.py` + `init_db.py`.

---

## Testing Requirements

- Unit tests for services and driver logic
- Integration tests for API endpoints (use httpx AsyncClient)
- Celery tasks: test with `task.apply()` in eager mode

---

## Code Review Checklist

- [ ] New model imported in `alembic/env.py` and `init_db.py`?
- [ ] New router registered in `main.py`?
- [ ] New Celery task module added to `celery_app.py` imports?
- [ ] RBAC applied to endpoints that modify state?
- [ ] Error cases return appropriate HTTP status codes?
- [ ] Celery tasks handle failures and update job status?
- [ ] No hardcoded secrets or credentials?

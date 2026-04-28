# Error Handling

> How errors are handled in this project.

---

## Overview

The backend uses FastAPI's `HTTPException` for API errors and Python's standard exception handling for internal logic. Celery workers catch all exceptions to update job status before re-raising.

---

## API Error Responses

All API errors use FastAPI's standard format:

```json
{"detail": "Human-readable error message"}
```

Status codes used:
- `400` — invalid request (bad state transition, invalid params)
- `401` — missing or invalid JWT / API key
- `403` — valid auth but insufficient role (RBAC)
- `404` — resource not found
- `409` — conflict (duplicate name, device already reserved)
- `500` — internal error (driver failure, unexpected exception)

---

## Error Handling Patterns

### API Layer

```python
@router.post("/{device_id}/state")
async def transition_state(device_id: int, body: DeviceStateTransition, db=Depends(get_db)):
    device = (await db.execute(select(Device).where(Device.id == device_id))).scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if not device.can_transition_to(body.state):
        raise HTTPException(status_code=400, detail=f"Cannot transition from {device.state.value} to {body.state.value}")
```

### Celery Workers

Workers must catch exceptions and update job status to FAILED:

```python
@celery_app.task(bind=True)
def run_test(self, job_id: int):
    with Session(sync_engine) as session:
        job = session.get(TestJob, job_id)
        try:
            job.status = JobStatus.RUNNING
            session.commit()
            # ... execute test ...
            job.status = JobStatus.COMPLETED
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
        finally:
            session.commit()
```

### Hardware Drivers

Driver methods catch internal exceptions and return safe defaults or re-raise:

```python
async def get_power_state(self) -> PowerState:
    try:
        # try pyghmi first, then ipmitool fallback
    except Exception:
        return PowerState.UNKNOWN
```

---

## Common Mistakes

### Not updating job status on failure
If a Celery task crashes without setting `status = FAILED`, the job stays in RUNNING forever. Always use try/finally.

### Swallowing driver exceptions silently
Driver methods that return `False` or `UNKNOWN` on failure should log the error. Silent failures make debugging impossible.

### Raising HTTPException inside services
Services should raise domain exceptions or return error indicators. Only API layer should raise `HTTPException`.

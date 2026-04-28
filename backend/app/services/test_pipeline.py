"""Test pipeline service - LAVA-inspired deploy → boot → test → collect → cleanup."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

import redis

from app.core.config import settings
from app.models.job import JobStatus, JobType, LogLevel

logger = logging.getLogger(__name__)

# Sync redis client for use inside Celery workers (which are sync)
_redis_client: redis.Redis | None = None


def get_sync_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL)
    return _redis_client


def publish_job_event(job_id: int, event: dict):
    """Publish a job event to Redis for WebSocket relay."""
    r = get_sync_redis()
    r.publish(f"job:{job_id}:status", json.dumps(event))


def add_job_log(session, job_id: int, message: str, level: LogLevel = LogLevel.INFO):
    """Insert a log row and publish it via Redis."""
    from app.models.job import TestJobLog

    log = TestJobLog(job_id=job_id, level=level, message=message, timestamp=datetime.now(timezone.utc))
    session.add(log)
    session.flush()

    publish_job_event(job_id, {
        "type": "log",
        "level": level.value,
        "message": message,
        "timestamp": log.timestamp.isoformat(),
    })


def update_job_status(session, job, new_status: JobStatus, error_message: str | None = None):
    """Transition job status, set timestamps, and publish event."""
    job.status = new_status
    now = datetime.now(timezone.utc)
    if new_status == JobStatus.RUNNING and job.started_at is None:
        job.started_at = now
    if new_status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
        job.finished_at = now
    if error_message:
        job.error_message = error_message
    session.flush()

    publish_job_event(job.id, {
        "type": "status",
        "status": new_status.value,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "error_message": error_message,
    })


class TestPipeline:
    """Base pipeline: deploy → boot → test → collect → cleanup.

    Each stage can be overridden per test type. The pipeline is executed
    synchronously inside a Celery worker process.
    """

    def __init__(self, session, job, device, driver):
        self.session = session
        self.job = job
        self.device = device
        self.driver = driver

    # --- pipeline stages ---

    def stage_deploy(self):
        """Prepare environment (no-op by default, override for PXE etc.)."""
        add_job_log(self.session, self.job.id, "Deploy stage: environment ready (no-op)")

    def stage_boot(self):
        """Verify the server is booted and reachable."""
        add_job_log(self.session, self.job.id, "Boot stage: verifying server is reachable")
        # In a real implementation this would SSH-ping or check power state
        # For now we just log it
        add_job_log(self.session, self.job.id, "Boot stage: server reachable")

    def stage_test(self):
        """Execute the actual test. Must be overridden by subclasses."""
        raise NotImplementedError

    def stage_collect(self):
        """Collect results. Default: mark result from job.result already set in stage_test."""
        add_job_log(self.session, self.job.id, "Collect stage: results stored")

    def stage_cleanup(self):
        """Cleanup (optional)."""
        add_job_log(self.session, self.job.id, "Cleanup stage: done")

    # --- runner ---

    def run(self):
        stages = [
            ("deploy", self.stage_deploy),
            ("boot", self.stage_boot),
            ("test", self.stage_test),
            ("collect", self.stage_collect),
            ("cleanup", self.stage_cleanup),
        ]
        for stage_name, stage_fn in stages:
            add_job_log(self.session, self.job.id, f"Starting stage: {stage_name}")
            publish_job_event(self.job.id, {"type": "stage", "stage": stage_name})
            stage_fn()
            add_job_log(self.session, self.job.id, f"Completed stage: {stage_name}")


class StressPipeline(TestPipeline):
    """Pipeline for stress tests (stressapptest / memtester / fio)."""

    def stage_test(self):
        config = self.job.config or {}
        tool = config.get("tool", "stressapptest")
        duration = config.get("duration_seconds", 3600)
        add_job_log(self.session, self.job.id, f"Stress test: tool={tool}, duration={duration}s")

        # Build command based on tool
        if tool == "stressapptest":
            cmd = f"stressapptest -s {duration}"
            if config.get("memory_mb"):
                cmd += f" -M {config['memory_mb']}"
        elif tool == "memtester":
            mem = config.get("memory_mb", 1024)
            cmd = f"memtester {mem}M 1"
        elif tool == "fio":
            target = config.get("io_target", "/tmp/fio_test")
            cmd = f"fio --name=stress --rw=randrw --bs=4k --size=1G --runtime={duration} --filename={target}"
            if config.get("extra_args"):
                cmd += f" {config['extra_args']}"
        else:
            cmd = tool

        add_job_log(self.session, self.job.id, f"Executing: {cmd}")
        # In production: SSH to device or send to agent. Here we record the command.
        self.job.result = {
            "tool": tool,
            "command": cmd,
            "status": "executed",
            "note": "Agent execution stub - replace with real SSH/Agent call",
        }
        self.session.flush()
        add_job_log(self.session, self.job.id, "Stress test command dispatched to agent")


class StabilityPipeline(TestPipeline):
    """Pipeline for stability tests (AC/DC/Reboot cycles)."""

    def stage_test(self):
        config = self.job.config or {}
        cycle_type = config.get("cycle_type", "reboot")
        cycle_count = config.get("cycle_count", 10)
        interval = config.get("interval_seconds", 60)
        wait_boot = config.get("wait_boot_seconds", 300)

        add_job_log(
            self.session, self.job.id,
            f"Stability test: type={cycle_type}, cycles={cycle_count}, interval={interval}s",
        )

        results = []
        for i in range(1, cycle_count + 1):
            add_job_log(self.session, self.job.id, f"Cycle {i}/{cycle_count}: starting {cycle_type}")
            publish_job_event(self.job.id, {
                "type": "progress",
                "current": i,
                "total": cycle_count,
            })

            try:
                # Use the hardware driver for power operations
                if cycle_type == "ac_cycle":
                    asyncio.run(self.driver.power_off(force=True))
                    import time; time.sleep(interval)
                    asyncio.run(self.driver.power_on())
                elif cycle_type == "dc_cycle":
                    asyncio.run(self.driver.power_cycle())
                elif cycle_type == "reboot":
                    asyncio.run(self.driver.power_reset())

                # Wait for boot
                add_job_log(self.session, self.job.id, f"Cycle {i}: waiting {wait_boot}s for boot")
                import time; time.sleep(min(wait_boot, 5))  # capped for dev; real: time.sleep(wait_boot)

                # Check power state
                state = asyncio.run(self.driver.get_power_state())
                cycle_result = {"cycle": i, "power_state": state.value, "status": "pass"}

                # Optionally check SEL
                if config.get("check_sel", True):
                    try:
                        sel = asyncio.run(self.driver.get_event_log(count=5))
                        cycle_result["sel_entries"] = len(sel)
                    except Exception:
                        cycle_result["sel_entries"] = "unavailable"

                results.append(cycle_result)
                add_job_log(self.session, self.job.id, f"Cycle {i}: completed, power={state.value}")

            except Exception as exc:
                results.append({"cycle": i, "status": "fail", "error": str(exc)})
                add_job_log(self.session, self.job.id, f"Cycle {i}: FAILED - {exc}", LogLevel.ERROR)

        passed = sum(1 for r in results if r.get("status") == "pass")
        self.job.result = {
            "cycle_type": cycle_type,
            "total_cycles": cycle_count,
            "passed": passed,
            "failed": cycle_count - passed,
            "cycles": results,
        }
        self.session.flush()


class PerformancePipeline(TestPipeline):
    """Pipeline for performance benchmarks."""

    def stage_test(self):
        config = self.job.config or {}
        benchmark = config.get("benchmark", "unixbench")
        iterations = config.get("iterations", 1)

        add_job_log(
            self.session, self.job.id,
            f"Performance test: benchmark={benchmark}, iterations={iterations}",
        )

        if benchmark == "unixbench":
            cmd = f"./Run -i {iterations}"
        elif benchmark == "specpu2017":
            suite = config.get("extra_args", "intrate")
            cmd = f"runcpu --config=default --iterations={iterations} {suite}"
        elif benchmark == "specjvm":
            cmd = f"java -jar SPECjvm2008.jar -i {iterations}"
        elif benchmark == "specjbb":
            cmd = "java -jar specjbb2015.jar -m composite"
        else:
            cmd = benchmark

        add_job_log(self.session, self.job.id, f"Executing: {cmd}")
        self.job.result = {
            "benchmark": benchmark,
            "command": cmd,
            "iterations": iterations,
            "status": "executed",
            "note": "Agent execution stub - replace with real SSH/Agent call",
        }
        self.session.flush()
        add_job_log(self.session, self.job.id, "Benchmark command dispatched to agent")


PIPELINE_MAP: dict[JobType, type[TestPipeline]] = {
    JobType.STRESS: StressPipeline,
    JobType.STABILITY: StabilityPipeline,
    JobType.PERFORMANCE: PerformancePipeline,
}

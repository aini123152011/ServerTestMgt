"""ServerTestLab Agent - lightweight agent that runs on DUT (Device Under Test).

Connects to the backend API, receives test tasks, executes them, and reports results.
"""

from __future__ import annotations

import logging
import signal
import sys
import time
from typing import Any

import requests

from agent.config import config
from agent.executors.stress import StressExecutor
from agent.executors.benchmark import BenchmarkExecutor
from agent.reporters.http_reporter import HttpReporter

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("stl-agent")

EXECUTORS = {
    "stress": StressExecutor(),
    "performance": BenchmarkExecutor(),
}

running = True


def signal_handler(sig, frame):
    global running
    logger.info("Shutdown signal received")
    running = False


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def poll_for_tasks(reporter: HttpReporter) -> dict | None:
    """Poll backend for pending tasks assigned to this agent."""
    try:
        resp = reporter.session.get(f"{reporter.server_url}/agent/tasks/next", timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception:
        return None


def execute_task(task: dict, reporter: HttpReporter):
    """Execute a single task received from the backend."""
    job_id = task.get("job_id")
    job_type = task.get("job_type")
    task_config = task.get("config", {})

    logger.info(f"Executing job {job_id}, type={job_type}")
    reporter.report_status(job_id, "running", "Agent started execution")

    executor = EXECUTORS.get(job_type)
    if not executor:
        reporter.report_status(job_id, "failed", f"No executor for job type: {job_type}")
        return

    if not executor.validate_config(task_config):
        reporter.report_status(job_id, "failed", "Invalid test configuration")
        return

    def report_fn(message: str):
        reporter.report_log(job_id, "info", message)

    try:
        result = executor.execute(task_config, report_fn=report_fn)
        reporter.report_result(job_id, {
            "success": result.success,
            "return_code": result.return_code,
            "stdout_tail": result.stdout[-2000:] if result.stdout else "",
            "stderr_tail": result.stderr[-2000:] if result.stderr else "",
            "metrics": result.metrics,
        })
        status = "completed" if result.success else "failed"
        reporter.report_status(job_id, status, f"Exit code: {result.return_code}")
    except Exception as exc:
        logger.exception(f"Task execution failed for job {job_id}")
        reporter.report_status(job_id, "failed", str(exc))


def main():
    logger.info(f"ServerTestLab Agent starting, server={config.SERVER_URL}")
    reporter = HttpReporter()

    last_heartbeat = 0.0

    while running:
        now = time.time()

        # Heartbeat
        if now - last_heartbeat >= config.HEARTBEAT_INTERVAL:
            reporter.heartbeat()
            last_heartbeat = now

        # Poll for tasks
        task = poll_for_tasks(reporter)
        if task:
            execute_task(task, reporter)
        else:
            time.sleep(5)

    logger.info("Agent stopped")


if __name__ == "__main__":
    main()

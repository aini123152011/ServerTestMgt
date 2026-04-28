"""HTTP reporter - sends results and status back to the ServerTestLab backend."""

from __future__ import annotations

import logging
from typing import Any

import requests

from agent.config import config

logger = logging.getLogger(__name__)


class HttpReporter:
    def __init__(self, server_url: str | None = None, token: str | None = None):
        self.server_url = (server_url or config.SERVER_URL).rstrip("/")
        self.token = token or config.AGENT_TOKEN
        self.session = requests.Session()
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"
        self.session.headers["Content-Type"] = "application/json"

    def report_status(self, job_id: int, status: str, message: str | None = None):
        """Report job status update to backend."""
        payload: dict[str, Any] = {"status": status}
        if message:
            payload["message"] = message
        try:
            resp = self.session.post(f"{self.server_url}/agent/jobs/{job_id}/status", json=payload, timeout=10)
            resp.raise_for_status()
        except Exception:
            logger.exception(f"Failed to report status for job {job_id}")

    def report_log(self, job_id: int, level: str, message: str):
        """Send a log line to backend."""
        try:
            self.session.post(
                f"{self.server_url}/agent/jobs/{job_id}/log",
                json={"level": level, "message": message},
                timeout=10,
            )
        except Exception:
            logger.debug(f"Failed to send log for job {job_id}")

    def report_result(self, job_id: int, result: dict):
        """Submit final test result."""
        try:
            resp = self.session.post(
                f"{self.server_url}/agent/jobs/{job_id}/result",
                json=result,
                timeout=30,
            )
            resp.raise_for_status()
        except Exception:
            logger.exception(f"Failed to report result for job {job_id}")

    def heartbeat(self, device_id: int | None = None):
        """Send heartbeat to backend."""
        payload: dict[str, Any] = {}
        if device_id:
            payload["device_id"] = device_id
        try:
            self.session.post(f"{self.server_url}/agent/heartbeat", json=payload, timeout=5)
        except Exception:
            logger.debug("Heartbeat failed")

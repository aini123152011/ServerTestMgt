"""Base executor interface for test agents."""

from __future__ import annotations

import abc
import subprocess
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    success: bool
    return_code: int = 0
    stdout: str = ""
    stderr: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)


class BaseExecutor(abc.ABC):
    """Base class for all test executors."""

    @abc.abstractmethod
    def validate_config(self, config: dict) -> bool:
        """Validate the test configuration before execution."""
        ...

    @abc.abstractmethod
    def execute(self, config: dict, report_fn=None) -> ExecutionResult:
        """Execute the test. report_fn(message) can be called to stream progress."""
        ...

    def run_command(self, cmd: str, timeout: int | None = None, report_fn=None) -> ExecutionResult:
        """Helper to run a shell command and capture output."""
        logger.info(f"Running: {cmd}")
        if report_fn:
            report_fn(f"Executing: {cmd}")
        try:
            proc = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=timeout,
            )
            return ExecutionResult(
                success=proc.returncode == 0,
                return_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(success=False, return_code=-1, stderr="Command timed out")
        except Exception as e:
            return ExecutionResult(success=False, return_code=-1, stderr=str(e))

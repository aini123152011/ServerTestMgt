"""Stress test executor - wraps stressapptest, memtester, fio."""

from __future__ import annotations

import logging

from agent.executors.base import BaseExecutor, ExecutionResult

logger = logging.getLogger(__name__)


class StressExecutor(BaseExecutor):
    SUPPORTED_TOOLS = ("stressapptest", "memtester", "fio")

    def validate_config(self, config: dict) -> bool:
        tool = config.get("tool", "stressapptest")
        if tool not in self.SUPPORTED_TOOLS:
            logger.error(f"Unsupported stress tool: {tool}")
            return False
        duration = config.get("duration_seconds", 0)
        if duration <= 0:
            logger.error("duration_seconds must be positive")
            return False
        return True

    def execute(self, config: dict, report_fn=None) -> ExecutionResult:
        tool = config.get("tool", "stressapptest")
        duration = config.get("duration_seconds", 3600)

        if tool == "stressapptest":
            cmd = f"stressapptest -s {duration}"
            if config.get("memory_mb"):
                cmd += f" -M {config['memory_mb']}"
            if config.get("cpu_workers"):
                cmd += f" -C {config['cpu_workers']}"

        elif tool == "memtester":
            mem = config.get("memory_mb", 1024)
            cmd = f"memtester {mem}M 1"

        elif tool == "fio":
            target = config.get("io_target", "/tmp/fio_test")
            cmd = (
                f"fio --name=stress --rw=randrw --bs=4k --size=1G "
                f"--runtime={duration} --time_based --filename={target} --output-format=json"
            )
            if config.get("extra_args"):
                cmd += f" {config['extra_args']}"
        else:
            return ExecutionResult(success=False, return_code=-1, stderr=f"Unknown tool: {tool}")

        result = self.run_command(cmd, timeout=duration + 300, report_fn=report_fn)

        # Parse fio JSON output for metrics
        if tool == "fio" and result.success:
            try:
                import json
                data = json.loads(result.stdout)
                jobs = data.get("jobs", [{}])
                if jobs:
                    j = jobs[0]
                    result.metrics = {
                        "read_iops": j.get("read", {}).get("iops", 0),
                        "write_iops": j.get("write", {}).get("iops", 0),
                        "read_bw_kbs": j.get("read", {}).get("bw", 0),
                        "write_bw_kbs": j.get("write", {}).get("bw", 0),
                    }
            except Exception:
                pass

        return result

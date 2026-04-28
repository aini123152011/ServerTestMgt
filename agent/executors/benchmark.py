"""Benchmark executor - wraps UnixBench, SPEC CPU 2017, etc."""

from __future__ import annotations

import logging
import re

from agent.executors.base import BaseExecutor, ExecutionResult

logger = logging.getLogger(__name__)


class BenchmarkExecutor(BaseExecutor):
    SUPPORTED_BENCHMARKS = ("unixbench", "specpu2017", "specjvm", "specjbb")

    def validate_config(self, config: dict) -> bool:
        benchmark = config.get("benchmark", "unixbench")
        if benchmark not in self.SUPPORTED_BENCHMARKS:
            logger.error(f"Unsupported benchmark: {benchmark}")
            return False
        return True

    def execute(self, config: dict, report_fn=None) -> ExecutionResult:
        benchmark = config.get("benchmark", "unixbench")
        iterations = config.get("iterations", 1)

        if benchmark == "unixbench":
            cmd = f"cd /opt/UnixBench && ./Run -i {iterations}"
        elif benchmark == "specpu2017":
            suite = config.get("extra_args", "intrate")
            cmd = f"cd /opt/cpu2017 && source shrc && runcpu --config=default --iterations={iterations} {suite}"
        elif benchmark == "specjvm":
            cmd = f"java -jar /opt/SPECjvm2008/SPECjvm2008.jar -i {iterations}"
        elif benchmark == "specjbb":
            cmd = "cd /opt/specjbb2015 && java -jar specjbb2015.jar -m composite"
        else:
            return ExecutionResult(success=False, return_code=-1, stderr=f"Unknown benchmark: {benchmark}")

        # Benchmarks can run for hours
        timeout = config.get("timeout_seconds", 86400)
        result = self.run_command(cmd, timeout=timeout, report_fn=report_fn)

        # Try to parse scores from output
        if result.success:
            result.metrics = self._parse_scores(benchmark, result.stdout)

        return result

    def _parse_scores(self, benchmark: str, stdout: str) -> dict:
        """Best-effort score extraction from benchmark output."""
        metrics: dict = {}
        if benchmark == "unixbench":
            # Look for "System Benchmarks Index Score" line
            match = re.search(r"System Benchmarks Index Score\s+(\d+\.?\d*)", stdout)
            if match:
                metrics["index_score"] = float(match.group(1))
        elif benchmark == "specpu2017":
            # Look for "Est. SPECrate" lines
            for m in re.finditer(r"Est\.\s+(SPECrate\S+)\s+=\s+(\d+\.?\d*)", stdout):
                metrics[m.group(1)] = float(m.group(2))
        return metrics

"""Report generation service."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device
from app.models.job import JobStatus, JobType, LogLevel, TestJob, TestJobLog
from app.models.user import User
from app.schemas.report import (
    ExportFormat,
    ReportData,
    ReportDeviceInfo,
    ReportJobInfo,
    ReportLogSummary,
    ReportSummary,
    ReportTimeline,
    ReportUserInfo,
)


class ReportService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_report(self, job_id: int) -> ReportData:
        """Generate a structured report for a completed job."""
        result = await self.db.execute(select(TestJob).where(TestJob.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            raise ValueError(f"Job {job_id} not found")

        device = job.device
        user = job.user

        # Calculate duration
        duration = None
        if job.started_at and job.finished_at:
            duration = (job.finished_at - job.started_at).total_seconds()

        job_info = ReportJobInfo(
            id=job.id,
            name=job.name,
            job_type=job.job_type.value,
            status=job.status.value,
            created_at=job.created_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            duration_seconds=duration,
            error_message=job.error_message,
        )

        device_info = ReportDeviceInfo(
            id=device.id,
            name=device.name,
            bmc_ip=device.bmc_ip,
            bmc_protocol=device.bmc_protocol.value,
            model=device.model,
            serial_number=device.serial_number,
            location=device.location,
        )

        user_info = ReportUserInfo(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
        )

        # Build timeline from logs
        logs_result = await self.db.execute(
            select(TestJobLog)
            .where(TestJobLog.job_id == job_id)
            .order_by(TestJobLog.timestamp)
        )
        logs = logs_result.scalars().all()

        timeline = []
        for log in logs:
            timeline.append(ReportTimeline(
                event=log.level.value,
                timestamp=log.timestamp,
                detail=log.message,
            ))

        # Log summary
        info_count = sum(1 for l in logs if l.level == LogLevel.INFO)
        warn_count = sum(1 for l in logs if l.level == LogLevel.WARNING)
        error_count = sum(1 for l in logs if l.level == LogLevel.ERROR)

        log_summary = ReportLogSummary(
            total=len(logs),
            info_count=info_count,
            warning_count=warn_count,
            error_count=error_count,
        )

        return ReportData(
            job_info=job_info,
            device_info=device_info,
            user_info=user_info,
            test_config=job.config or {},
            results=job.result or {},
            timeline=timeline,
            log_summary=log_summary,
            generated_at=datetime.now(timezone.utc),
        )

    async def export_json(self, job_id: int) -> str:
        report = await self.generate_report(job_id)
        return report.model_dump_json(indent=2)

    async def export_csv(self, job_id: int) -> str:
        report = await self.generate_report(job_id)
        output = io.StringIO()
        writer = csv.writer(output)

        # Header section
        writer.writerow(["Section", "Field", "Value"])
        writer.writerow(["Job", "ID", report.job_info.id])
        writer.writerow(["Job", "Name", report.job_info.name])
        writer.writerow(["Job", "Type", report.job_info.job_type])
        writer.writerow(["Job", "Status", report.job_info.status])
        writer.writerow(["Job", "Created", report.job_info.created_at.isoformat()])
        writer.writerow(["Job", "Started", report.job_info.started_at.isoformat() if report.job_info.started_at else ""])
        writer.writerow(["Job", "Finished", report.job_info.finished_at.isoformat() if report.job_info.finished_at else ""])
        writer.writerow(["Job", "Duration(s)", report.job_info.duration_seconds or ""])
        writer.writerow(["Device", "Name", report.device_info.name])
        writer.writerow(["Device", "BMC IP", report.device_info.bmc_ip])
        writer.writerow(["Device", "Model", report.device_info.model or ""])
        writer.writerow(["User", "Username", report.user_info.username])

        # Config
        for k, v in report.test_config.items():
            writer.writerow(["Config", k, json.dumps(v) if isinstance(v, (dict, list)) else v])

        # Results
        for k, v in report.results.items():
            writer.writerow(["Result", k, json.dumps(v) if isinstance(v, (dict, list)) else v])

        # Timeline
        writer.writerow([])
        writer.writerow(["Timestamp", "Level", "Message"])
        for entry in report.timeline:
            writer.writerow([entry.timestamp.isoformat(), entry.event, entry.detail or ""])

        return output.getvalue()

    async def export_html(self, job_id: int) -> str:
        report = await self.generate_report(job_id)
        ji = report.job_info
        di = report.device_info
        ui = report.user_info

        config_rows = "".join(
            f"<tr><td>{k}</td><td>{json.dumps(v) if isinstance(v, (dict, list)) else v}</td></tr>"
            for k, v in report.test_config.items()
        )
        result_rows = "".join(
            f"<tr><td>{k}</td><td>{json.dumps(v) if isinstance(v, (dict, list)) else v}</td></tr>"
            for k, v in report.results.items()
        )
        log_rows = "".join(
            f'<tr class="{e.event}"><td>{e.timestamp.strftime("%Y-%m-%d %H:%M:%S")}</td>'
            f"<td>{e.event}</td><td>{e.detail or ''}</td></tr>"
            for e in report.timeline
        )

        status_class = "pass" if ji.status == "completed" else "fail"
        duration_str = f"{ji.duration_seconds:.1f}s" if ji.duration_seconds else "N/A"

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>Test Report - {ji.name}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 40px; color: #333; }}
h1 {{ color: #1a1a2e; border-bottom: 2px solid #409eff; padding-bottom: 10px; }}
h2 {{ color: #304156; margin-top: 30px; }}
table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
th {{ background: #f5f7fa; font-weight: 600; }}
.pass {{ color: #67c23a; }} .fail {{ color: #f56c6c; }}
.info td:nth-child(2) {{ color: #409eff; }}
.warning td:nth-child(2) {{ color: #e6a23c; }}
.error td:nth-child(2) {{ color: #f56c6c; }}
.summary {{ display: flex; gap: 20px; margin: 20px 0; }}
.summary-card {{ background: #f5f7fa; border-radius: 8px; padding: 16px 24px; flex: 1; text-align: center; }}
.summary-card .value {{ font-size: 24px; font-weight: bold; color: #409eff; }}
.summary-card .label {{ color: #909399; margin-top: 4px; }}
.meta {{ color: #909399; font-size: 13px; margin-top: 30px; }}
</style>
</head>
<body>
<h1>Test Report: {ji.name}</h1>
<div class="summary">
  <div class="summary-card"><div class="value {status_class}">{ji.status.upper()}</div><div class="label">Status</div></div>
  <div class="summary-card"><div class="value">{ji.job_type}</div><div class="label">Test Type</div></div>
  <div class="summary-card"><div class="value">{duration_str}</div><div class="label">Duration</div></div>
  <div class="summary-card"><div class="value">{report.log_summary.error_count}</div><div class="label">Errors</div></div>
</div>

<h2>Job Information</h2>
<table>
<tr><th>Field</th><th>Value</th></tr>
<tr><td>Job ID</td><td>{ji.id}</td></tr>
<tr><td>Name</td><td>{ji.name}</td></tr>
<tr><td>Type</td><td>{ji.job_type}</td></tr>
<tr><td>Status</td><td class="{status_class}">{ji.status}</td></tr>
<tr><td>Created</td><td>{ji.created_at.strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
<tr><td>Started</td><td>{ji.started_at.strftime('%Y-%m-%d %H:%M:%S') if ji.started_at else 'N/A'}</td></tr>
<tr><td>Finished</td><td>{ji.finished_at.strftime('%Y-%m-%d %H:%M:%S') if ji.finished_at else 'N/A'}</td></tr>
<tr><td>Duration</td><td>{duration_str}</td></tr>
</table>

<h2>Device Information</h2>
<table>
<tr><th>Field</th><th>Value</th></tr>
<tr><td>Device</td><td>{di.name}</td></tr>
<tr><td>BMC IP</td><td>{di.bmc_ip}</td></tr>
<tr><td>Protocol</td><td>{di.bmc_protocol}</td></tr>
<tr><td>Model</td><td>{di.model or 'N/A'}</td></tr>
<tr><td>Serial</td><td>{di.serial_number or 'N/A'}</td></tr>
<tr><td>Location</td><td>{di.location or 'N/A'}</td></tr>
</table>

<h2>Operator</h2>
<table>
<tr><th>Field</th><th>Value</th></tr>
<tr><td>Username</td><td>{ui.username}</td></tr>
<tr><td>Full Name</td><td>{ui.full_name or 'N/A'}</td></tr>
</table>

<h2>Test Configuration</h2>
<table><tr><th>Parameter</th><th>Value</th></tr>{config_rows}</table>

<h2>Test Results</h2>
<table><tr><th>Metric</th><th>Value</th></tr>{result_rows}</table>

<h2>Execution Log ({report.log_summary.total} entries)</h2>
<table><tr><th>Timestamp</th><th>Level</th><th>Message</th></tr>{log_rows}</table>

<div class="meta">
Report generated at {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
</div>
</body>
</html>"""

    async def get_summary(self) -> ReportSummary:
        """Aggregate summary across all jobs."""
        # Total counts by status
        status_counts = await self.db.execute(
            select(TestJob.status, func.count(TestJob.id))
            .group_by(TestJob.status)
        )
        counts_map: dict[str, int] = {}
        total = 0
        for status_val, cnt in status_counts.all():
            counts_map[status_val.value if hasattr(status_val, 'value') else status_val] = cnt
            total += cnt

        completed = counts_map.get("completed", 0)
        failed = counts_map.get("failed", 0)
        cancelled = counts_map.get("cancelled", 0)
        finished = completed + failed
        pass_rate = (completed / finished * 100) if finished > 0 else 0.0

        # Average duration of completed jobs
        avg_result = await self.db.execute(
            select(func.avg(
                func.extract("epoch", TestJob.finished_at) - func.extract("epoch", TestJob.started_at)
            )).where(
                TestJob.status == JobStatus.COMPLETED,
                TestJob.started_at.isnot(None),
                TestJob.finished_at.isnot(None),
            )
        )
        avg_duration = avg_result.scalar_one_or_none()

        # Breakdown by type
        type_counts = await self.db.execute(
            select(TestJob.job_type, TestJob.status, func.count(TestJob.id))
            .group_by(TestJob.job_type, TestJob.status)
        )
        by_type: dict[str, dict[str, int]] = {}
        for jtype, jstatus, cnt in type_counts.all():
            type_key = jtype.value if hasattr(jtype, 'value') else jtype
            status_key = jstatus.value if hasattr(jstatus, 'value') else jstatus
            if type_key not in by_type:
                by_type[type_key] = {}
            by_type[type_key][status_key] = cnt

        return ReportSummary(
            total_jobs=total,
            completed_jobs=completed,
            failed_jobs=failed,
            cancelled_jobs=cancelled,
            pass_rate=round(pass_rate, 1),
            avg_duration_seconds=round(avg_duration, 1) if avg_duration else None,
            by_type=by_type,
        )

"""Report API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.report import ExportFormat, ReportData, ReportSummary
from app.services.report_service import ReportService

router = APIRouter()


@router.get("/summary", response_model=ReportSummary)
async def get_report_summary(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get aggregate summary of all test jobs."""
    svc = ReportService(db)
    return await svc.get_summary()


@router.get("/{job_id}", response_model=ReportData)
async def get_report(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get structured report data for a job."""
    svc = ReportService(db)
    try:
        return await svc.generate_report(job_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{job_id}/export")
async def export_report(
    job_id: int,
    format: ExportFormat = ExportFormat.JSON,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Export report as JSON, CSV, or HTML file."""
    svc = ReportService(db)
    try:
        if format == ExportFormat.JSON:
            content = await svc.export_json(job_id)
            return Response(
                content=content,
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename=report_{job_id}.json"},
            )
        elif format == ExportFormat.CSV:
            content = await svc.export_csv(job_id)
            return Response(
                content=content,
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=report_{job_id}.csv"},
            )
        elif format == ExportFormat.HTML:
            content = await svc.export_html(job_id)
            return Response(
                content=content,
                media_type="text/html",
                headers={"Content-Disposition": f"attachment; filename=report_{job_id}.html"},
            )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

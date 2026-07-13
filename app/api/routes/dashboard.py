"""Dashboard data endpoints — JSON only (spec: backend serves the admin dashboard)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.crud import employee as employee_crud
from app.crud import snapshot as snapshot_crud
from app.db.session import get_db
from app.schemas.dashboard import EmployeeDashboard, EmployeeRead, SnapshotRead
from app.schemas.overview import OverviewResponse
from app.services.analysis import run_analysis_for_employee
from app.services.cron import run_hourly_batch
from app.services.overview import build_overview

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=OverviewResponse)
def overview(
    company_id: str | None = Query(None), db: Session = Depends(get_db)
) -> OverviewResponse:
    """Org-wide aggregate for the dashboard landing page: KPI tiles (+deltas vs
    the previous hour), flattened pending replies, and the hourly volume series."""
    return build_overview(db, company_id)


@router.get("/employees", response_model=list[EmployeeRead])
def list_employees(
    company_id: str | None = Query(None), db: Session = Depends(get_db)
) -> list:
    return employee_crud.list_employees(db, company_id)


@router.get("/employees/{employee_id}", response_model=EmployeeDashboard)
def employee_dashboard(employee_id: str, db: Session = Depends(get_db)) -> EmployeeDashboard:
    emp = employee_crud.get_employee(db, employee_id)
    if emp is None:
        raise HTTPException(status_code=404, detail="employee not found")
    latest = snapshot_crud.latest_snapshot(db, employee_id)
    return EmployeeDashboard(
        employee=EmployeeRead.model_validate(emp),
        latest_snapshot=SnapshotRead.model_validate(latest) if latest else None,
        snapshot_count=snapshot_crud.count_snapshots(db, employee_id),
    )


@router.get("/employees/{employee_id}/snapshots", response_model=list[SnapshotRead])
def employee_snapshots(
    employee_id: str,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list:
    if employee_crud.get_employee(db, employee_id) is None:
        raise HTTPException(status_code=404, detail="employee not found")
    return snapshot_crud.list_snapshots(db, employee_id, limit=limit, offset=offset)


# ── Manual triggers (useful for testing without waiting for the hour) ──────────

@router.post("/employees/{employee_id}/run-now")
async def run_now(employee_id: str, db: Session = Depends(get_db)) -> dict:
    emp = employee_crud.get_employee(db, employee_id)
    if emp is None:
        raise HTTPException(status_code=404, detail="employee not found")
    status = await run_analysis_for_employee(db, emp)
    return {"employee_id": employee_id, "status": status}


@router.post("/cron/run-now")
async def cron_run_now() -> dict:
    tally = await run_hourly_batch()
    return {"tally": tally}

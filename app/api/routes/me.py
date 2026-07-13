"""Employee self-service — the logged-in salesperson sees only their OWN mailbox
analysis, and connects their own Outlook. Scoped entirely by the session token,
so an employee can never read a colleague's data.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.crud import employee as employee_crud
from app.crud import snapshot as snapshot_crud
from app.db.session import get_db
from app.schemas.dashboard import EmployeeDashboard, EmployeeRead, SnapshotRead
from app.services.session import get_session_user

router = APIRouter(prefix="/me", tags=["me"])


def _own_employee(db: Session, user: dict):
    """Resolve the session's own employee row, or 403 for a non-employee session."""
    emp_id = user.get("employee_id")
    if not emp_id:
        raise HTTPException(status_code=403, detail="this view is for employees")
    emp = employee_crud.get_employee(db, emp_id)
    if emp is None:
        raise HTTPException(status_code=404, detail="employee not found")
    return emp


@router.get("/dashboard", response_model=EmployeeDashboard)
def my_dashboard(
    db: Session = Depends(get_db), user: dict = Depends(get_session_user)
) -> EmployeeDashboard:
    emp = _own_employee(db, user)
    latest = snapshot_crud.latest_snapshot(db, emp.id)
    return EmployeeDashboard(
        employee=EmployeeRead.model_validate(emp),
        latest_snapshot=SnapshotRead.model_validate(latest) if latest else None,
        snapshot_count=snapshot_crud.count_snapshots(db, emp.id),
    )


@router.get("/snapshots", response_model=list[SnapshotRead])
def my_snapshots(
    limit: int = 50,
    db: Session = Depends(get_db),
    user: dict = Depends(get_session_user),
) -> list:
    emp = _own_employee(db, user)
    return snapshot_crud.list_snapshots(db, emp.id, limit=min(limit, 200), offset=0)


@router.post("/outlook/dev-connect")
def dev_connect_outlook(
    db: Session = Depends(get_db), user: dict = Depends(get_session_user)
) -> dict:
    """DEV ONLY — mark the employee's Outlook connected without the real Microsoft
    consent (which needs Azure). Lets the employee flow be walked end-to-end now."""
    if settings.ENVIRONMENT != "development":
        raise HTTPException(status_code=404, detail="not found")
    emp = _own_employee(db, user)
    emp.outlook_connected = True
    emp.provider_email = emp.email
    emp.needs_reprovision = False
    db.add(emp)
    db.commit()
    return {"outlook_connected": True, "provider_email": emp.provider_email}

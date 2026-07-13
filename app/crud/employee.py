from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company, Employee


def get_employee(db: Session, employee_id: str) -> Employee | None:
    return db.get(Employee, employee_id)


def get_by_company_email(db: Session, company_id: str, email: str) -> Employee | None:
    return db.scalar(
        select(Employee).where(Employee.company_id == company_id, Employee.email == email)
    )


def list_employees(db: Session, company_id: str | None = None) -> list[Employee]:
    stmt = select(Employee)
    if company_id:
        stmt = stmt.where(Employee.company_id == company_id)
    return list(db.scalars(stmt.order_by(Employee.created_at)))


def list_active_for_cron(db: Session) -> list[Employee]:
    """Employees eligible for the hourly run: Outlook connected, not flagged."""
    return list(
        db.scalars(
            select(Employee).where(
                Employee.outlook_connected.is_(True),
                Employee.needs_reprovision.is_(False),
            )
        )
    )


def get_company(db: Session, company_id: str) -> Company | None:
    return db.get(Company, company_id)

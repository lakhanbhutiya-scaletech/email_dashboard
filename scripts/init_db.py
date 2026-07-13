"""Dev-only: create all tables directly (skips Alembic).

Handy for a fresh local start. For anything beyond local dev use Alembic:
    uv run alembic revision --autogenerate -m "init"
    uv run alembic upgrade head
"""

from app.db.base import Base
from app.db.session import engine
from app import models  # noqa: F401  registers tables


def main() -> None:
    Base.metadata.create_all(bind=engine)
    print("tables created:", ", ".join(sorted(Base.metadata.tables)))


if __name__ == "__main__":
    main()

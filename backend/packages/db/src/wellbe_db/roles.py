from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def verify_role_grants(
    session: AsyncSession,
    expected_role: str,
    table: str,
    allowed_privileges: list[str],
) -> bool:
    result = await session.execute(
        text("""
            SELECT privilege_type
            FROM information_schema.role_table_grants
            WHERE grantee = :role
              AND table_name = :table
        """),
        {"role": expected_role, "table": table},
    )
    actual = {row[0] for row in result.fetchall()}
    expected = {p.upper() for p in allowed_privileges}
    return actual == expected

"""Frontdesk admin CLI.

Usage:
    uv run python -m src.cli admin grant  <email>
    uv run python -m src.cli admin revoke <email>

Promotes or demotes a user to/from platform super-admin. The user must already
exist (register them via the app first).
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from src.application.shared.unit_of_work import UnitOfWork
from src.bootstrap.container import set_platform_admin_use_case
from src.domain.shared.exceptions import EntityNotFoundError
from src.infrastructure.persistence.postgres.database import async_session_factory


async def _set_admin(email: str, *, granted: bool) -> int:
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        try:
            is_admin = await set_platform_admin_use_case(uow).execute(email=email, granted=granted)
            await session.commit()
        except EntityNotFoundError as exc:
            await session.rollback()
            print(f"error: {exc}", file=sys.stderr)
            return 1
    verb = "granted to" if is_admin else "revoked from"
    print(f"platform-admin {verb} {email}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="src.cli", description="Frontdesk admin CLI")
    sub = parser.add_subparsers(dest="group", required=True)

    admin = sub.add_parser("admin", help="Platform-admin management")
    admin_sub = admin.add_subparsers(dest="action", required=True)
    grant = admin_sub.add_parser("grant", help="Grant platform-admin to a user")
    grant.add_argument("email")
    revoke = admin_sub.add_parser("revoke", help="Revoke platform-admin from a user")
    revoke.add_argument("email")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.group == "admin":
        granted = args.action == "grant"
        return asyncio.run(_set_admin(args.email, granted=granted))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

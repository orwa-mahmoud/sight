"""ListTenantsForAdmin — cross-tenant listing for the platform admin."""

from __future__ import annotations

from src.application.admin.dtos import AdminTenantDTO
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.users.entities import UserTenant
from src.domain.users.value_objects import UserTenantRole


class ListTenantsForAdmin:
    """Returns every tenant with its owner email and basic usage counts.

    Admin views are low-traffic, so per-tenant count queries are acceptable
    here rather than a single denormalized aggregate.
    """

    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self) -> list[AdminTenantDTO]:
        tenants = await self._uow.tenants.list_all()
        rows: list[AdminTenantDTO] = []
        for tenant in tenants:
            links = await self._uow.user_tenants.list_for_tenant(tenant.id)
            owner_email = await self._resolve_owner_email(links)
            # Re-scope per tenant so the document count is correct under RLS
            # (the platform admin reads across every tenant).
            await self._uow.set_tenant_scope(tenant.id)
            doc_count = await self._uow.documents.count_for_tenant(tenant.id)
            rows.append(
                AdminTenantDTO(
                    id=tenant.id,
                    name=tenant.name,
                    slug=tenant.slug,
                    status=tenant.status.value,
                    owner_email=owner_email,
                    user_count=len(links),
                    document_count=doc_count,
                )
            )
        return rows

    async def _resolve_owner_email(self, links: list[UserTenant]) -> str | None:
        owner_link = next((link for link in links if link.role == UserTenantRole.OWNER), None)
        if owner_link is None:
            return None
        owner = await self._uow.users.get_by_id(owner_link.user_id)
        return owner.email if owner else None

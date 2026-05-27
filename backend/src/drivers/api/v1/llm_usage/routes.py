"""LLM usage routes — owner-only access to their own tenant's rollup."""

from __future__ import annotations

from fastapi import APIRouter

from src.application.llm_usage.queries import GetTenantUsageStats
from src.application.llm_usage.use_cases.get_usage_stats import GetTenantUsageStatsUseCase
from src.domain.shared.exceptions import AuthenticationError
from src.drivers.api.dependencies import CurrentUser, UnitOfWorkDep
from src.drivers.api.v1.llm_usage.schemas import UsageStatsResponse

router = APIRouter(prefix="/llm-usage", tags=["llm-usage"])


@router.get("/stats")
async def stats(current_user: CurrentUser, uow: UnitOfWorkDep) -> UsageStatsResponse:
    """Aggregated usage for the caller's tenant.

    Resolves tenant from the user's membership (v1 = single tenant per user).
    """
    links = await uow.user_tenants.list_for_user(current_user.id)
    if not links:
        # `get_current_user` already validates the user, but defend in depth.
        raise AuthenticationError("User is not associated with any tenant")
    tenant_id = links[0].tenant_id

    dto = await GetTenantUsageStatsUseCase(uow=uow).execute(GetTenantUsageStats(tenant_id=tenant_id))
    return UsageStatsResponse(
        total_input_tokens=dto.total_input_tokens,
        total_output_tokens=dto.total_output_tokens,
        total_cache_read_tokens=dto.total_cache_read_tokens,
        total_input_cost=dto.total_input_cost,
        total_cache_read_cost=dto.total_cache_read_cost,
        total_output_cost=dto.total_output_cost,
        total_cost=dto.total_cost,
        total_calls=dto.total_calls,
    )

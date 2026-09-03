"""Server-side authorization policy. The browser never supplies any of these values."""

from dataclasses import dataclass

from app.models import Environment, Role


@dataclass(frozen=True)
class RolePolicy:
    approval_limit_cents: int | None
    editable_flag_environments: frozenset[Environment]

    @property
    def can_edit_staging_flags(self) -> bool:
        return Environment.STAGING in self.editable_flag_environments

    @property
    def can_edit_production_flags(self) -> bool:
        return Environment.PRODUCTION in self.editable_flag_environments


ROLE_POLICIES: dict[Role, RolePolicy] = {
    Role.SUPPORT_AGENT: RolePolicy(
        approval_limit_cents=50_000,
        editable_flag_environments=frozenset(),
    ),
    Role.OPERATIONS_MANAGER: RolePolicy(
        approval_limit_cents=500_000,
        editable_flag_environments=frozenset({Environment.STAGING}),
    ),
    Role.ADMIN: RolePolicy(
        approval_limit_cents=None,
        editable_flag_environments=frozenset({Environment.STAGING, Environment.PRODUCTION}),
    ),
}


def policy_for(role: Role) -> RolePolicy:
    return ROLE_POLICIES[role]

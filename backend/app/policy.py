"""Server-side authorization policy. The browser never supplies any of these values.

Everything here is pure: no database, no HTTP. The workflow service turns a `Denial`
into the matching error response.
"""

from dataclasses import dataclass
from enum import Enum

from app.models import Environment, Role

SUPPORTED_CURRENCY = "USD"


class RefundAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    ESCALATE = "escalate"


@dataclass(frozen=True)
class RolePolicy:
    approval_limit_cents: int | None
    editable_flag_environments: frozenset[Environment]
    can_escalate_refunds: bool

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
        can_escalate_refunds=True,
    ),
    Role.OPERATIONS_MANAGER: RolePolicy(
        approval_limit_cents=500_000,
        editable_flag_environments=frozenset({Environment.STAGING}),
        can_escalate_refunds=True,
    ),
    Role.ADMIN: RolePolicy(
        approval_limit_cents=None,
        editable_flag_environments=frozenset({Environment.STAGING, Environment.PRODUCTION}),
        can_escalate_refunds=False,
    ),
}


def policy_for(role: Role) -> RolePolicy:
    return ROLE_POLICIES[role]


@dataclass(frozen=True)
class Denial:
    code: str
    details: dict[str, object]


UNSUPPORTED_CURRENCY = "UNSUPPORTED_CURRENCY"
ACTION_NOT_PERMITTED_FOR_ROLE = "ACTION_NOT_PERMITTED_FOR_ROLE"
APPROVAL_LIMIT_EXCEEDED = "APPROVAL_LIMIT_EXCEEDED"


def refund_action_denial(
    role: Role, action: RefundAction, amount_cents: int, currency: str
) -> Denial | None:
    """Return why `role` may not perform `action` on a refund of this amount, or None if allowed.

    Refund status is deliberately not an input: this answers "may this role ever do this to
    this amount"; the workflow service separately checks the state machine.
    """
    if currency != SUPPORTED_CURRENCY:
        return Denial(
            UNSUPPORTED_CURRENCY,
            {"currency": currency, "supported_currency": SUPPORTED_CURRENCY},
        )

    policy = policy_for(role)

    if action is RefundAction.ESCALATE:
        if not policy.can_escalate_refunds:
            return Denial(
                ACTION_NOT_PERMITTED_FOR_ROLE,
                {"role": role.value, "action": action.value},
            )
        return None

    limit = policy.approval_limit_cents
    if limit is not None and amount_cents > limit:
        return Denial(
            APPROVAL_LIMIT_EXCEEDED,
            {
                "role": role.value,
                "action": action.value,
                "amount_cents": amount_cents,
                "approval_limit_cents": limit,
            },
        )
    return None

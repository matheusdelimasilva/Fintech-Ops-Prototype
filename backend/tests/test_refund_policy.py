"""Pure policy tests: no database, no HTTP."""

import pytest

from app.models import Role
from app.policy import (
    ACTION_NOT_PERMITTED_FOR_ROLE,
    APPROVAL_LIMIT_EXCEEDED,
    UNSUPPORTED_CURRENCY,
    RefundAction,
    refund_action_denial,
)

SUPPORT = Role.SUPPORT_AGENT
OPS = Role.OPERATIONS_MANAGER
ADMIN = Role.ADMIN
DECIDING_ACTIONS = [RefundAction.APPROVE, RefundAction.REJECT]

# The five amounts that matter: one inside, on, and just past each finite limit.
AMOUNTS = [49_999, 50_000, 50_001, 500_000, 500_001]
LIMITS: dict[Role, int | None] = {SUPPORT: 50_000, OPS: 500_000, ADMIN: None}


@pytest.mark.parametrize("amount_cents", AMOUNTS)
@pytest.mark.parametrize("action", DECIDING_ACTIONS)
@pytest.mark.parametrize("role", list(Role))
def test_approval_limits_are_inclusive_per_role(
    role: Role, action: RefundAction, amount_cents: int
) -> None:
    limit = LIMITS[role]
    denial = refund_action_denial(role, action, amount_cents, "USD")

    if limit is None or amount_cents <= limit:
        assert denial is None
    else:
        assert denial is not None
        assert denial.code == APPROVAL_LIMIT_EXCEEDED
        assert denial.details == {
            "role": role.value,
            "action": action.value,
            "amount_cents": amount_cents,
            "approval_limit_cents": limit,
        }


def test_admin_has_no_upper_bound() -> None:
    assert refund_action_denial(ADMIN, RefundAction.APPROVE, 10_000_000_000, "USD") is None


@pytest.mark.parametrize("amount_cents", AMOUNTS)
@pytest.mark.parametrize("role", list(Role))
def test_escalation_depends_on_role_not_amount(role: Role, amount_cents: int) -> None:
    denial = refund_action_denial(role, RefundAction.ESCALATE, amount_cents, "USD")

    if role is ADMIN:
        assert denial is not None
        assert denial.code == ACTION_NOT_PERMITTED_FOR_ROLE
        assert denial.details == {"role": "admin", "action": "escalate"}
    else:
        assert denial is None


@pytest.mark.parametrize("action", list(RefundAction))
@pytest.mark.parametrize("role", list(Role))
def test_unsupported_currency_fails_closed_for_every_role_and_action(
    role: Role, action: RefundAction
) -> None:
    denial = refund_action_denial(role, action, 1, "EUR")

    assert denial is not None
    assert denial.code == UNSUPPORTED_CURRENCY
    assert denial.details == {"currency": "EUR", "supported_currency": "USD"}

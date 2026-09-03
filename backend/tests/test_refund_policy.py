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


@pytest.mark.parametrize("action", DECIDING_ACTIONS)
@pytest.mark.parametrize(
    ("role", "amount_cents", "allowed"),
    [
        (SUPPORT, 49_999, True),
        (SUPPORT, 50_000, True),
        (SUPPORT, 50_001, False),
        (SUPPORT, 500_000, False),
        (OPS, 50_001, True),
        (OPS, 500_000, True),
        (OPS, 500_001, False),
        (ADMIN, 500_001, True),
        (ADMIN, 10_000_000_000, True),
    ],
)
def test_approval_limits_are_inclusive_per_role(
    role: Role, action: RefundAction, amount_cents: int, allowed: bool
) -> None:
    denial = refund_action_denial(role, action, amount_cents, "USD")

    if allowed:
        assert denial is None
    else:
        assert denial is not None
        assert denial.code == APPROVAL_LIMIT_EXCEEDED
        assert denial.details["amount_cents"] == amount_cents
        assert denial.details["approval_limit_cents"] == {SUPPORT: 50_000, OPS: 500_000}[role]
        assert denial.details["action"] == action.value


@pytest.mark.parametrize("amount_cents", [100, 50_001, 500_001])
@pytest.mark.parametrize("role", [SUPPORT, OPS])
def test_support_and_ops_may_escalate_any_amount(role: Role, amount_cents: int) -> None:
    assert refund_action_denial(role, RefundAction.ESCALATE, amount_cents, "USD") is None


def test_admin_may_not_escalate() -> None:
    denial = refund_action_denial(ADMIN, RefundAction.ESCALATE, 100, "USD")

    assert denial is not None
    assert denial.code == ACTION_NOT_PERMITTED_FOR_ROLE
    assert denial.details == {"role": "admin", "action": "escalate"}


@pytest.mark.parametrize("action", list(RefundAction))
@pytest.mark.parametrize("role", list(Role))
def test_unsupported_currency_fails_closed_for_every_role_and_action(
    role: Role, action: RefundAction
) -> None:
    denial = refund_action_denial(role, action, 1, "EUR")

    assert denial is not None
    assert denial.code == UNSUPPORTED_CURRENCY
    assert denial.details == {"currency": "EUR", "supported_currency": "USD"}

"""Pure policy tests for feature-flag editing: no database, no HTTP."""

import pytest

from app.models import Environment, Role
from app.policy import ACTION_NOT_PERMITTED_FOR_ROLE, feature_flag_edit_denial, policy_for

EDITABLE: dict[Role, set[Environment]] = {
    Role.SUPPORT_AGENT: set(),
    Role.OPERATIONS_MANAGER: {Environment.STAGING},
    Role.ADMIN: {Environment.STAGING, Environment.PRODUCTION},
}


@pytest.mark.parametrize("environment", list(Environment))
@pytest.mark.parametrize("role", list(Role))
def test_edit_permission_matrix(role: Role, environment: Environment) -> None:
    denial = feature_flag_edit_denial(role, environment)

    if environment in EDITABLE[role]:
        assert denial is None
    else:
        assert denial is not None
        assert denial.code == ACTION_NOT_PERMITTED_FOR_ROLE
        assert denial.details == {
            "role": role.value,
            "action": "edit_feature_flag",
            "environment": environment.value,
            "editable_environments": sorted(e.value for e in EDITABLE[role]),
        }


@pytest.mark.parametrize("role", list(Role))
def test_matrix_agrees_with_session_policy_booleans(role: Role) -> None:
    policy = policy_for(role)

    assert policy.can_edit_staging_flags is (
        feature_flag_edit_denial(role, Environment.STAGING) is None
    )
    assert policy.can_edit_production_flags is (
        feature_flag_edit_denial(role, Environment.PRODUCTION) is None
    )

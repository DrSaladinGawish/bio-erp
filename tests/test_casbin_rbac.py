import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.cells.rbac_cell.casbin_adapter import get_enforcer


@pytest.fixture
def enforcer():
    os.environ["RBAC_MODEL_CONF"] = "app/cells/rbac_cell/policy_model.conf"
    os.environ["RBAC_POLICY_CSV"] = "app/cells/rbac_cell/policy.csv"
    return get_enforcer()


class TestCasbinEnforcement:
    def test_admin_can_export_report(self, enforcer):
        assert enforcer.enforce("admin", "report", "export", "tenant_a")

    def test_admin_can_manage_rbac(self, enforcer):
        assert enforcer.enforce("admin", "rbac", "manage", "any_tenant")

    def test_cost_viewer_can_export(self, enforcer):
        assert enforcer.enforce("cost_viewer", "report", "export", "default")

    def test_cost_viewer_can_read_scm(self, enforcer):
        assert enforcer.enforce("cost_viewer", "scm", "read", "default")

    def test_cost_viewer_cannot_write_scm(self, enforcer):
        assert not enforcer.enforce("cost_viewer", "scm", "write", "default")

    def test_cost_viewer_cannot_manage_rbac(self, enforcer):
        assert not enforcer.enforce("cost_viewer", "rbac", "manage", "default")

    def test_or_analyst_can_run_engine(self, enforcer):
        assert enforcer.enforce("or_analyst", "or_engine", "run", "prod")

    def test_or_analyst_cannot_write_scm(self, enforcer):
        assert not enforcer.enforce("or_analyst", "scm", "write", "prod")

    def test_unknown_role_denied(self, enforcer):
        assert not enforcer.enforce("hacker", "report", "export", "default")

    def test_auditor_can_export_report(self, enforcer):
        assert enforcer.enforce("auditor", "report", "export", "default")

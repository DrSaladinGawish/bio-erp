import pytest

from app.tasks.auto_trigger_tasks import _dispatch_trigger


class TestAutoTriggerTasks:
    def test_dispatch_job_created(self):
        result = _dispatch_trigger("job_created", {"job_id": "j_001"})
        assert result["action"] == "validate_job"
        assert result["job_id"] == "j_001"

    def test_dispatch_cost_threshold(self):
        result = _dispatch_trigger("cost_threshold", {"value": 50000})
        assert result["action"] == "notify_approver"
        assert result["threshold"] == 50000

    def test_dispatch_scm_update(self):
        result = _dispatch_trigger("scm_update", {"scm_id": "scm_99"})
        assert result["action"] == "recalc_strategic_cost"
        assert result["scm_id"] == "scm_99"

    def test_dispatch_sustainability(self):
        result = _dispatch_trigger("sustainability_check", {"project": "green"})
        assert result["action"] == "generate_sustainability_report"

    def test_dispatch_unknown_trigger(self):
        with pytest.raises(ValueError, match="Unknown trigger type"):
            _dispatch_trigger("nonexistent", {})

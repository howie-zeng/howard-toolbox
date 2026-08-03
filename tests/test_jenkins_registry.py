# tests/test_jenkins_registry.py
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROUTINES = Path(__file__).resolve().parents[1] / "claude-code-routines"
if str(_ROUTINES) not in sys.path:
    sys.path.insert(0, str(_ROUTINES))

from jenkins_monitor import registry  # noqa: E402
from jenkins_monitor.models import BuildInfo  # noqa: E402

REGISTRY_PATH = _ROUTINES / "jenkins-jobs.yaml"


def test_registry_has_all_25_jobs():
    specs = registry.load_registry(REGISTRY_PATH)
    assert len(specs) == 25


def test_tier_split_is_22_fix_and_3_notify():
    specs = registry.load_registry(REGISTRY_PATH)
    tiers = [s.tier for s in specs.values()]
    assert tiers.count("fix") == 22
    assert tiers.count("notify") == 3


def test_deploy_jobs_are_notify_only():
    specs = registry.load_registry(REGISTRY_PATH)
    for name in ("quant-deploy-lmqr", "quant-deploy-lmsimdata", "quant-deploy-Rcode"):
        assert specs[name].tier == "notify"
        assert specs[name].trigger_type == "pollscm"


def test_intex_is_friday_only_not_daily():
    """Regression: the name says Daily but the cron is Friday-only."""
    spec = registry.load_registry(REGISTRY_PATH)["quant-DailySimDataUpdateIntex"]
    assert spec.cron == "0 16 * * 5"
    assert spec.trigger_type == "cron"


def test_resitracking_unload_is_daily_despite_monthly_name():
    spec = registry.load_registry(REGISTRY_PATH)["quant-Monthly-ResiTracking-Unload"]
    assert spec.cron == "H 2 * * *"


def test_lp_marks_unstable_as_failure_with_eight_markers():
    spec = registry.load_registry(REGISTRY_PATH)["quant-DailySimDataUpdateLP"]
    assert spec.unstable_is_failure is True
    assert len(spec.success_markers) == 8


def test_crt_update_console_is_not_informative():
    """wh_crt_update --log does not mirror errors to stdout."""
    spec = registry.load_registry(REGISTRY_PATH)["quant-DailySimDataUpdate"]
    assert spec.console_informative is False
    assert spec.nas_log_glob is not None


def test_orchestrators_flagged_with_child_job():
    specs = registry.load_registry(REGISTRY_PATH)
    orch = specs["quant-tracking-report-recache-workflow"]
    assert orch.orchestrator is True
    assert orch.child_job == "quant-tracking-report-recache"


def test_upstream_strict_defaults_false_and_parses_true_from_yaml(tmp_path):
    """No job in the live registry sets upstream_strict - every upstream job is
    conditionally gated - but the field must still parse when a future strictly
    chained child opts in."""
    specs = registry.load_registry(REGISTRY_PATH)
    upstream_specs = [s for s in specs.values() if s.trigger_type == "upstream"]
    assert upstream_specs  # sanity: the registry actually has upstream-triggered jobs
    assert all(s.upstream_strict is False for s in upstream_specs)

    strict_yaml = tmp_path / "strict.yaml"
    strict_yaml.write_text(
        "jobs:\n"
        "  - job: quant-x\n"
        "    tier: fix\n"
        "    family: f\n"
        "    trigger_type: upstream\n"
        "    upstream: quant-parent\n"
        "    upstream_strict: true\n",
        encoding="utf-8",
    )
    parsed = registry.load_registry(strict_yaml)
    assert parsed["quant-x"].upstream_strict is True


def test_unknown_trigger_type_is_rejected(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "jobs:\n  - job: quant-x\n    tier: fix\n    family: f\n    trigger_type: wishful\n",
        encoding="utf-8",
    )
    with pytest.raises(registry.RegistryError, match="trigger_type"):
        registry.load_registry(bad)


def test_cron_trigger_requires_cron_and_tz(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "jobs:\n  - job: quant-x\n    tier: fix\n    family: f\n    trigger_type: cron\n",
        encoding="utf-8",
    )
    with pytest.raises(registry.RegistryError, match="cron"):
        registry.load_registry(bad)


def test_malformed_yaml_is_rejected(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("jobs: [\n", encoding="utf-8")
    with pytest.raises(registry.RegistryError, match="invalid YAML"):
        registry.load_registry(bad)


def test_null_jobs_value_is_rejected(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("jobs:\n", encoding="utf-8")
    with pytest.raises(registry.RegistryError, match="jobs"):
        registry.load_registry(bad)


def test_non_mapping_job_entry_is_rejected(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text('jobs:\n  - "just a string"\n', encoding="utf-8")
    with pytest.raises(registry.RegistryError, match="mapping"):
        registry.load_registry(bad)


def test_buildinfo_did_work_excludes_not_built():
    assert BuildInfo(1, "SUCCESS", None, False).did_work is True
    assert BuildInfo(2, "FAILURE", None, False).did_work is True
    assert BuildInfo(3, "UNSTABLE", None, False).did_work is True
    assert BuildInfo(4, "NOT_BUILT", None, False).did_work is False
    assert BuildInfo(5, None, None, True).did_work is False

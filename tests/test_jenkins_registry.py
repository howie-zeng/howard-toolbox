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


def test_upstream_trigger_requires_a_named_parent(tmp_path):
    """The parent name is what lets the agent apply rule 9 (a gated child running less often
    than its parent is normal). An upstream job without one leaves that unjudgeable."""
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "jobs:\n  - job: quant-x\n    tier: fix\n    family: f\n    trigger_type: upstream\n",
        encoding="utf-8",
    )
    with pytest.raises(registry.RegistryError, match="requires 'upstream'"):
        registry.load_registry(bad)


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


# --- Final review, IMPORTANT 6: validation gaps that escaped RegistryError and killed the
# --- whole unattended run. `tz` was checked for presence but never resolved, and
# --- cadence.previous_fire_time's ZoneInfo(tzname) raises ZoneInfoNotFoundError (a
# --- KeyError), which cli.py's per-job isolation catches only CadenceError for. Same shape
# --- for float(entry["grace_hours"]) raising a bare ValueError.


def test_unresolvable_timezone_is_rejected_at_load_time(tmp_path):
    """One typo ('America/New_Yrok') used to abort every job's report, not just its own."""
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "jobs:\n"
        "  - job: quant-x\n"
        "    tier: fix\n"
        "    family: f\n"
        "    trigger_type: cron\n"
        '    cron: "0 12 * * *"\n'
        "    tz: America/New_Yrok\n",
        encoding="utf-8",
    )
    with pytest.raises(registry.RegistryError, match="quant-x"):
        registry.load_registry(bad)


def test_non_numeric_grace_hours_is_rejected_with_job_and_field_named(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "jobs:\n"
        "  - job: quant-x\n"
        "    tier: fix\n"
        "    family: f\n"
        "    trigger_type: cron\n"
        '    cron: "0 12 * * *"\n'
        "    tz: America/New_York\n"
        "    grace_hours: abc\n",
        encoding="utf-8",
    )
    with pytest.raises(registry.RegistryError, match="grace_hours"):
        registry.load_registry(bad)


def test_non_numeric_max_silence_days_is_rejected(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "jobs:\n"
        "  - job: quant-x\n"
        "    tier: fix\n"
        "    family: f\n"
        "    trigger_type: upstream\n"
        "    upstream: quant-parent\n"
        "    max_silence_days: three weeks\n",
        encoding="utf-8",
    )
    with pytest.raises(registry.RegistryError, match="max_silence_days"):
        registry.load_registry(bad)


def test_orchestrator_without_child_job_is_rejected(tmp_path):
    """`orchestrator: true` alone silently disables drill-down (diagnose.py requires both)
    and then tries to extract a traceback from a wrapper console that never has one."""
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "jobs:\n  - job: quant-x\n    tier: fix\n    family: f\n    trigger_type: manual\n    orchestrator: true\n",
        encoding="utf-8",
    )
    with pytest.raises(registry.RegistryError, match="child_job"):
        registry.load_registry(bad)


def test_success_markers_as_bare_string_is_rejected(tmp_path):
    """tuple("Done NQM") iterates into single-character 'markers', each trivially present
    in any console - so nothing is ever reported missing and a partial failure looks whole."""
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "jobs:\n"
        "  - job: quant-x\n"
        "    tier: fix\n"
        "    family: f\n"
        "    trigger_type: manual\n"
        '    success_markers: "Done NQM"\n',
        encoding="utf-8",
    )
    with pytest.raises(registry.RegistryError, match="success_markers"):
        registry.load_registry(bad)


# --- Final review, CRITICAL 3 / IMPORTANT 3: registry-level assertions on the new defaults.


def test_every_upstream_job_has_an_absolute_silence_ceiling():
    """Non-strict upstream jobs have no cadence check at all, so the ceiling is the only
    staleness signal they have. A new upstream job added without it is invisible forever."""
    specs = registry.load_registry(REGISTRY_PATH)
    upstream = [s for s in specs.values() if s.trigger_type == "upstream"]
    assert upstream
    missing = [s.job for s in upstream if s.max_silence_days is None]
    assert missing == [], f"upstream jobs with no max_silence_days ceiling: {missing}"
    assert all(s.max_silence_days == 21 for s in upstream)


def test_pollscm_and_manual_jobs_are_intentionally_exempt_from_the_ceiling():
    specs = registry.load_registry(REGISTRY_PATH)
    exempt = [s for s in specs.values() if s.trigger_type in ("pollscm", "manual")]
    assert exempt
    assert all(s.max_silence_days is None for s in exempt)


def test_unstable_is_failure_defaults_true_for_jobs_that_do_not_mention_it():
    """GREEN must mean 'confirmed good', not 'UNSTABLE and we chose not to look'."""
    specs = registry.load_registry(REGISTRY_PATH)
    assert all(s.unstable_is_failure is True for s in specs.values())


def test_unstable_is_failure_can_still_be_opted_out_explicitly(tmp_path):
    lenient = tmp_path / "lenient.yaml"
    lenient.write_text(
        "jobs:\n"
        "  - job: quant-x\n"
        "    tier: fix\n"
        "    family: f\n"
        "    trigger_type: manual\n"
        "    unstable_is_failure: false\n",
        encoding="utf-8",
    )
    assert registry.load_registry(lenient)["quant-x"].unstable_is_failure is False


def test_resitracking_pipeline_is_no_longer_flagged_orchestrator_without_a_child():
    """It had orchestrator: true and no child_job. `orchestrator` was dropped rather than a
    child job invented, because no child name is verified from the jenkinsfile."""
    spec = registry.load_registry(REGISTRY_PATH)["quant-Monthly-ResiTracking-pipeline"]
    assert spec.orchestrator is False
    assert spec.child_job is None


def test_every_orchestrator_in_the_live_registry_has_a_child_job():
    specs = registry.load_registry(REGISTRY_PATH)
    for spec in specs.values():
        if spec.orchestrator:
            assert spec.child_job, f"{spec.job}: orchestrator with no child_job"

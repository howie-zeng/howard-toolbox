# tests/test_jenkins_report.py
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROUTINES = Path(__file__).resolve().parents[1] / "claude-code-routines"
if str(_ROUTINES) not in sys.path:
    sys.path.insert(0, str(_ROUTINES))

from jenkins_monitor import report  # noqa: E402
from jenkins_monitor.models import Diagnosis, Finding, JobStatus, State  # noqa: E402


def _f(job, state, transition, diagnosis=None, previous_state=None):
    return Finding(
        status=JobStatus(job=job, state=state, detail="because reasons"),
        transition=transition,
        diagnosis=diagnosis,
        previous_state=previous_state,
    )


def test_header_states_scope_and_token_status():
    out = report.render([], token_ok=True, total_jobs=25)
    assert "### Jenkins Job Monitor" in out
    assert "25" in out
    assert "Token: OK" in out


def test_missing_token_is_reported_loudly_and_never_as_all_clear():
    out = report.render([], token_ok=False, total_jobs=25)
    assert "UNREACHABLE" in out
    assert "all clear" not in out.lower()
    assert "cannot" in out.lower() or "could not" in out.lower()


def test_all_green_says_so_explicitly():
    out = report.render([], token_ok=True, total_jobs=25)
    assert "No new failures" in out


def test_new_failure_appears_before_ongoing():
    out = report.render(
        [_f("b", State.RED, "ONGOING"), _f("a", State.RED, "NEW")],
        token_ok=True,
        total_jobs=25,
    )
    assert out.index("NEW failures") < out.index("Ongoing")


def test_recovered_job_is_reported():
    out = report.render([_f("a", State.GREEN, "RECOVERED")], token_ok=True, total_jobs=25)
    assert "Recovered" in out
    assert "a" in out


def test_diagnosis_renders_error_class_and_affected():
    d = Diagnosis(
        job="a",
        error_class="KeyError",
        error_text="KeyError: 'Transition'",
        source_hint="crt_deal.py:214 in get_collat_trans_df",
        affected=("NONQM_PSEUDO", "HELOC_PSEUDO"),
    )
    out = report.render([_f("a", State.RED, "NEW", d)], token_ok=True, total_jobs=25)
    assert "KeyError" in out
    assert "crt_deal.py:214" in out
    assert "NONQM_PSEUDO" in out


def test_capped_jobs_are_named_so_cap_is_not_mistaken_for_all_clear():
    out = report.render([], token_ok=True, total_jobs=25, capped=["x", "y"])
    assert "slot cap" in out.lower()
    assert "x" in out and "y" in out


def test_seed_only_and_never_did_work_explained_as_benign_or_investigate():
    out = report.render(
        [_f("s", State.SEED_ONLY, "NEW"), _f("n", State.NEVER_DID_WORK, "ONGOING")],
        token_ok=True,
        total_jobs=25,
    )
    assert "seed" in out.lower()
    assert "investigat" in out.lower()


def test_scope_line_omits_breakdown_when_tier_counts_are_zero():
    out = report.render([], token_ok=True, total_jobs=25)
    assert "auto-fix" not in out.lower()
    assert "notify-only" not in out.lower()


def test_scope_line_shows_breakdown_when_tier_counts_given():
    out = report.render([], token_ok=True, total_jobs=25, fix_count=10, notify_count=15)
    assert "10" in out and "auto-fix" in out.lower()
    assert "15" in out and "notify-only" in out.lower()


# --- Task 5 regression risk: ONGOING findings whose current state is BUILDING or
# --- SEED_ONLY are NOT confirmed recoveries. A bare "ONGOING - BUILDING" line reads
# --- as neutral. The renderer must thread the previous state through and spell out
# --- that recovery is unconfirmed, without using wording that could itself read as
# --- an all-clear.


def test_ongoing_red_to_building_shows_arrow_transition():
    out = report.render(
        [_f("a", State.BUILDING, "ONGOING", previous_state=State.RED)],
        token_ok=True,
        total_jobs=25,
    )
    assert "RED" in out
    assert "BUILDING" in out
    # previous -> current must be threaded through, not a bare current-state line
    assert "RED -> BUILDING" in out


def test_ongoing_red_to_building_flags_recovery_not_confirmed():
    out = report.render(
        [_f("a", State.BUILDING, "ONGOING", previous_state=State.RED)],
        token_ok=True,
        total_jobs=25,
    )
    assert "not yet confirmed" in out.lower()
    # Must not read as an all-clear anywhere in the report: since this is the only
    # finding and it is ONGOING (not RECOVERED), the word "recovered" must not
    # appear at all - our own "recovery not yet confirmed" phrasing must not
    # accidentally contain it either.
    assert "recovered" not in out.lower()


def test_ongoing_stale_to_seed_only_flags_recovery_not_confirmed():
    out = report.render(
        [_f("a", State.SEED_ONLY, "ONGOING", previous_state=State.STALE)],
        token_ok=True,
        total_jobs=25,
    )
    assert "STALE -> SEED_ONLY" in out
    assert "not yet confirmed" in out.lower()
    assert "recovered" not in out.lower()


def test_new_finding_with_no_previous_state_shows_bare_current_state():
    out = report.render([_f("a", State.RED, "NEW")], token_ok=True, total_jobs=25)
    # no previous_state supplied -> no "->" transition marker, just the plain state.
    # This must still fail if the arrow (ASCII or Unicode) were wrongly emitted here.
    assert "->" not in out
    assert "RED" in out


def test_recovered_finding_can_show_previous_state_arrow():
    out = report.render(
        [_f("a", State.GREEN, "RECOVERED", previous_state=State.RED)],
        token_ok=True,
        total_jobs=25,
    )
    assert "RED -> GREEN" in out
    # a confirmed recovery is fine to call recovered - this is the one case where
    # the word is warranted, since state diff only labels RECOVERED for confirmed GREEN.
    assert "recovered" in out.lower()


# --- Task 7 Fix pass 1 (Finding 1, CRITICAL): the report is printed to a console,
# --- written to a .md file, and folded into an email pipeline (send_outlook_summary.py).
# --- report.py cannot know whether any given consumer has been hardened for Unicode, so
# --- its own output must be safe standalone. This is the real deliverable of the fix -
# --- without it, a Unicode regression here can silently return and crash an unattended
# --- run with zero output for a genuine failure.


def test_render_output_encodes_cleanly_on_default_windows_console():
    out = report.render(
        [_f("a", State.BUILDING, "ONGOING", previous_state=State.RED)],
        token_ok=True,
        total_jobs=25,
    )
    try:
        out.encode("cp1252")
    except UnicodeEncodeError as exc:  # pragma: no cover - documents the exact failure mode
        raise AssertionError(
            "report output must encode cleanly to cp1252, the default codepage of an "
            "unattended Windows console - a non-ASCII character here would crash the "
            "render with zero output for a genuine finding, the exact failure class this "
            "monitor exists to eliminate"
        ) from exc


# --- Task 7 Fix pass 1 (Finding 2, minor): render() only reads back the NEW / ONGOING /
# --- RECOVERED buckets, so an unrecognized transition value used to be silently absent
# --- from the output with no error - the "silently dropped finding" failure mode this
# --- project must not have. It is currently unreachable because statediff.label() only
# --- emits those three strings, but nothing enforced that, so harden it directly.


def test_unexpected_transition_raises_instead_of_silently_dropping():
    with pytest.raises(ValueError, match="bogus-job"):
        report.render(
            [_f("bogus-job", State.RED, "SOMETHING_ELSE")],
            token_ok=True,
            total_jobs=25,
        )

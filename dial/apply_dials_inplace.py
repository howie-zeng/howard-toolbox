"""Apply a dial spec to a model JSON IN PLACE, preserving formatting and Version fields.

Why this exists instead of `update_dials.py --spec ...`:

  1. `update_dials.py :: main()` always calls `update_all_versions()`, which recursively
     rewrites EVERY "Version" key to one value. Real submodel files carry heterogeneous
     versions (e.g. stacr_v1.8.2_submodel.json has 100x "v1.8.2" plus 11x "V1.0" and
     1x "V1.1" on sub-components) -- bumping flattens all of them.
  2. `update_dials.py :: save_json()` writes indent=4. The deployed submodel files are
     indent=2 with no trailing newline, so that reformats the whole file and buries the
     Shock change in a 100KB diff.

This script reuses the real dial logic (`apply_dial_overrides`) and only changes the writer.
It refuses to run unless an untouched round-trip reproduces the input byte-for-byte, so a
formatting mismatch fails loudly instead of silently reformatting.

Usage:
    python dial/apply_dials_inplace.py --spec dial/<spec>.json [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from update_dials import apply_dial_overrides  # noqa: E402

_LEAD = re.compile(r"\s*([0-9]+(?:\.[0-9]+)?)x")


def dumps_like(data: dict) -> str:
    """Serialize in the deployed submodel convention: indent=2, no trailing newline."""
    return json.dumps(data, indent=2)


def dial_snapshot(cfg: dict) -> dict[str, str]:
    """Map 'State.Transition[Cohort]' -> leading multiplier, for every Shock in the file."""
    out: dict[str, str] = {}

    def record(label: str, shock) -> None:
        if not isinstance(shock, dict):
            return
        if "Cohorts" in shock:
            for entry in shock.get("Cohorts") or []:
                detail = entry.get("Detail", "")
                m = _LEAD.match(detail)
                out[f"{label}[{entry.get('Cohort')}]"] = m.group(1) if m else "?"
        else:
            m = _LEAD.match(shock.get("Detail") or "")
            out[label] = m.group(1) if m else "?"

    for state, sdef in (cfg.get("State") or {}).items():
        for key, trans in (sdef.get("Transitions") or {}).items():
            record(f"{state}.{key}", trans.get("Shock"))
            detail = trans.get("Detail")
            if isinstance(detail, dict):
                for sub, sdefn in detail.items():
                    if isinstance(sdefn, dict):
                        record(f"{state}.{key}@{sub}", sdefn.get("Shock"))
    return out


def version_snapshot(cfg: dict) -> list[str]:
    found: list[str] = []

    def walk(node) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "Version":
                    found.append(str(v))
                else:
                    walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(cfg)
    return sorted(found)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spec", type=Path, required=True)
    ap.add_argument("--dry-run", action="store_true", help="report the diff without writing")
    args = ap.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    src = Path(spec["input"])
    dst = Path(spec.get("output", spec["input"]))
    overrides = spec["overrides"]

    if "version" in spec:
        raise SystemExit(
            "Spec carries a 'version' key. This script never bumps Version fields "
            "(see module docstring). Remove it, or use update_dials.py knowingly."
        )

    original = src.read_text(encoding="utf-8")
    cfg = json.loads(original)

    # Gate: an untouched round-trip must reproduce the source exactly, or our writer
    # convention does not match this file and we would reformat it.
    if dumps_like(json.loads(original)) != original:
        raise SystemExit(
            f"FORMATTING GATE FAILED for {src}: json.dumps(indent=2) does not reproduce "
            "the file byte-for-byte. Writing would reformat it. Inspect before proceeding."
        )
    print(f"[gate] round-trip reproduces {src.name} byte-for-byte ({len(original)} bytes)")

    before_dials = dial_snapshot(cfg)
    before_versions = version_snapshot(cfg)

    apply_dial_overrides(cfg, overrides)

    after_dials = dial_snapshot(cfg)
    after_versions = version_snapshot(cfg)

    if before_versions != after_versions:
        raise SystemExit("Version fields changed unexpectedly -- aborting.")
    print(f"[gate] {len(after_versions)} Version fields unchanged")

    changed = {k: (before_dials.get(k), v) for k, v in after_dials.items() if before_dials.get(k) != v}
    removed = sorted(set(before_dials) - set(after_dials))
    added = sorted(set(after_dials) - set(before_dials))

    print(f"\n[diff] {len(changed)} dial(s) changed:")
    for k, (old, new) in sorted(changed.items()):
        print(f"    {k:32s} {old} -> {new}")
    if added:
        print(f"[diff] shocks ADDED: {added}")
    if removed:
        print(f"[diff] shocks REMOVED: {removed}")
    untouched = len(after_dials) - len(changed)
    print(f"[diff] {untouched} existing shock(s) untouched")

    updated = dumps_like(cfg)
    if args.dry_run:
        print(f"\n[dry-run] would write {len(updated)} bytes to {dst} -- not written")
        return 0

    dst.write_text(updated, encoding="utf-8", newline="")
    print(f"\nWrote {dst} ({len(updated)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_INPUT = Path("data/STACR/stacr_v1.8.0.json")
DEFAULT_OUTPUT: Optional[Path] = None
DEFAULT_VERSION: Optional[str] = None

# Use a JSON spec file to define overrides (recommended).

_VERSION_RE = re.compile(
    r"^(?P<prefix>[Vv]?)(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch_prefix>[Vv]?)(?P<patch>\d+)(?:\.(?P<extra_prefix>[Vv]?)(?P<extra>\d+))?$"
)
_VERSION_IN_FILENAME_RE = re.compile(
    r"(?P<prefix>[Vv]?)(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch_prefix>[Vv]?)(?P<patch>\d+)(?:\.(?P<extra_prefix>[Vv]?)(?P<extra>\d+))?"
)


def _split_version(version: str) -> tuple[str, str, str, str, str, str, Optional[str]]:
    match = _VERSION_RE.match(version.strip())
    if not match:
        raise ValueError(f"Unrecognized version format: {version!r}")
    extra = match.group("extra")
    extra_prefix = match.group("extra_prefix") or ""
    if extra is None:
        extra_prefix = ""
    return (
        match.group("prefix"),
        match.group("major"),
        match.group("minor"),
        match.group("patch_prefix"),
        match.group("patch"),
        extra_prefix,
        extra,
    )


def _bump_version_string(version: str) -> str:
    prefix, major, minor, patch_prefix, patch, extra_prefix, extra = _split_version(version)
    if extra is not None:
        bumped = int(extra) + 1
        return f"{prefix}{major}.{minor}.{patch_prefix}{patch}.{extra_prefix}{bumped}"
    return f"{prefix}{major}.{minor}.{patch_prefix}{int(patch) + 1}"


def _replace_version_in_filename(name: str, version: str) -> Optional[str]:
    _split_version(version)
    match = _VERSION_IN_FILENAME_RE.search(name)
    if not match:
        return None
    return f"{name[:match.start()]}{version}{name[match.end():]}"


def _parse_target_shorthand(value: str) -> Dict[str, str]:
    if not isinstance(value, str):
        raise ValueError("Target shorthand must be a string")
    raw, _, detail = value.partition("@")
    state, sep, transition = raw.partition("->")
    state = state.strip()
    transition = transition.strip()
    detail = detail.strip()
    if not sep or not state or not transition:
        raise ValueError(
            "Target shorthand must be 'STATE->TRANSITION' or 'STATE->TRANSITION@DETAIL'"
        )
    target = {"state": state, "transition": transition}
    if detail:
        target["detail"] = detail
    return target


def _format_target_shorthand(state: str, transition: str, detail: Optional[str]) -> str:
    value = f"{state}->{transition}"
    if detail:
        value = f"{value}@{detail}"
    return value


def dial(x: float) -> str:
    """Builds a dial string with a flat period then linear ramp to 1.0x."""
    x = round(x, 3)
    parts = [f"{x}x for 36"]
    for i in range(1, 24):
        val = round(((24 - i) * x + i - 1) / 23, 3)
        parts.append(f"{val}x for 1")
    parts.append("1.0x for 1")
    parts.append("1x")
    return " ".join(parts)


def _is_identity_dial(value: float) -> bool:
    return round(float(value), 3) == 1.0


def update_all_versions(node: Any, new_version: str) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "Version":
                node[key] = new_version
            else:
                update_all_versions(value, new_version)
    elif isinstance(node, list):
        for item in node:
            update_all_versions(item, new_version)


def _get_transition_root(data: Dict[str, Any], state: str, transition: str) -> Dict[str, Any]:
    try:
        return data["State"][state]["Transitions"][transition]
    except KeyError as exc:
        raise KeyError(
            f"Missing transition path: State['{state}'].Transitions['{transition}']"
        ) from exc


def _target_for_shock(
    data: Dict[str, Any], state: str, transition: str, detail: Optional[str]
) -> Dict[str, Any]:
    transition_root = _get_transition_root(data, state, transition)
    if detail is None:
        return transition_root

    detail_root = transition_root.get("Detail")
    if not isinstance(detail_root, dict) or detail not in detail_root:
        raise KeyError(
            f"Missing detail path: State['{state}'].Transitions['{transition}'].Detail['{detail}']"
        )
    return detail_root[detail]


def _format_path(state: str, transition: str, detail: Optional[str]) -> str:
    path = f"State['{state}'].Transitions['{transition}']"
    if detail is not None:
        path += f".Detail['{detail}']"
    return path


def _upsert_simple_shock(
    target: Dict[str, Any],
    state: str,
    transition: str,
    detail: Optional[str],
    start_date: str,
    dial_value: float,
) -> None:
    shock = target.get("Shock")
    if isinstance(shock, dict) and ("Cohorts" in shock or shock.get("HasCohort")):
        raise ValueError(f"Refusing to overwrite cohort shock at {_format_path(state, transition, detail)}")
    target["Shock"] = {"StartDate": start_date, "Detail": dial(dial_value)}


def _ensure_cohort_shock(
    target: Dict[str, Any],
    path: str,
    allow_create: bool,
    allow_convert: bool,
) -> Dict[str, Any]:
    shock = target.get("Shock")
    if shock is None:
        if not allow_create:
            raise ValueError(f"Missing cohort shock at {path}. Set add_cohort to create.")
        shock = {"HasCohort": True, "Cohorts": []}
        target["Shock"] = shock

    if not isinstance(shock, dict):
        raise ValueError(f"Shock at {path} must be an object")

    if "Cohorts" not in shock:
        if shock.get("HasCohort") is True:
            shock["Cohorts"] = []
        elif allow_convert:
            shock = {"HasCohort": True, "Cohorts": []}
            target["Shock"] = shock
        else:
            raise ValueError(f"Refusing to overwrite non-cohort shock at {path} with a cohort dial")

    if shock.get("HasCohort") is not True:
        shock["HasCohort"] = True

    if not isinstance(shock["Cohorts"], list):
        raise ValueError(f"Shock.Cohorts at {path} must be a list")

    return shock


def _upsert_cohort_shock(
    target: Dict[str, Any],
    state: str,
    transition: str,
    detail: Optional[str],
    cohort: str,
    start_date: str,
    dial_value: float,
    add_cohort: bool,
    convert_cohort: bool,
) -> None:
    add_cohort = add_cohort or convert_cohort
    path = _format_path(state, transition, detail)
    shock = _ensure_cohort_shock(
        target,
        path,
        allow_create=add_cohort,
        allow_convert=convert_cohort,
    )
    cohorts = shock["Cohorts"]

    matches = [entry for entry in cohorts if entry.get("Cohort") == cohort]
    if not matches:
        if not add_cohort:
            raise KeyError(f"Missing cohort '{cohort}' at {path}. Set add_cohort to create.")
        entry = {"Cohort": cohort}
        cohorts.append(entry)
        matches = [entry]

    for entry in matches:
        entry["StartDate"] = start_date
        entry["Detail"] = dial(dial_value)


def _remove_shock(
    target: Dict[str, Any],
    state: str,
    transition: str,
    detail: Optional[str],
    cohort: Optional[str],
) -> None:
    shock = target.get("Shock")
    if shock is None:
        return

    if cohort is None:
        target.pop("Shock", None)
        return

    if not _is_cohort_shock(shock):
        target.pop("Shock", None)
        return

    cohorts = shock.get("Cohorts")
    if not isinstance(cohorts, list):
        return

    remaining = [entry for entry in cohorts if entry.get("Cohort") != cohort]
    if len(remaining) == len(cohorts):
        return

    if remaining:
        shock["Cohorts"] = remaining
    else:
        target.pop("Shock", None)


def _expand_override_targets(override: Dict[str, Any]) -> List[Dict[str, Any]]:
    targets = override.get("targets")
    target = override.get("target")
    if targets is not None and target is not None:
        raise ValueError("Override cannot include both target and targets")
    if targets is None and target is None:
        return [override]
    if "state" in override or "transition" in override:
        raise ValueError("Override with targets must not include state/transition")

    base = {
        key: value
        for key, value in override.items()
        if key not in {"targets", "target"}
    }

    if target is not None:
        merged = dict(base)
        merged.update(_parse_target_shorthand(target))
        return [merged]

    if not isinstance(targets, list) or not targets:
        raise ValueError("Override.targets must be a non-empty list")

    expanded: List[Dict[str, Any]] = []
    for target_entry in targets:
        if isinstance(target_entry, str):
            target_dict = _parse_target_shorthand(target_entry)
        elif isinstance(target_entry, dict):
            if "state" not in target_entry or "transition" not in target_entry:
                raise KeyError("Each target must include state and transition")
            target_dict = target_entry
        else:
            raise ValueError("Each target must be an object or shorthand string")
        merged = dict(base)
        merged.update(target_dict)
        expanded.append(merged)
    return expanded


def _apply_dial_override(data: Dict[str, Any], override: Dict[str, Any]) -> None:
    state = override["state"]
    transition = override["transition"]
    detail = override.get("detail")
    start_date = override["start_date"]
    dial_value = override["dial"]

    target = _target_for_shock(data, state, transition, detail)
    cohort = override.get("cohort")
    if _is_identity_dial(dial_value):
        _remove_shock(target, state, transition, detail, cohort)
        return
    if cohort is not None:
        convert_cohort = override.get("convert_cohort", True)
        _upsert_cohort_shock(
            target,
            state,
            transition,
            detail,
            cohort,
            start_date,
            dial_value,
            override.get("add_cohort", False),
            convert_cohort,
        )
    else:
        _upsert_simple_shock(
            target,
            state,
            transition,
            detail,
            start_date,
            dial_value,
        )


def apply_dial_overrides(
    data: Dict[str, Any],
    overrides: List[Dict[str, Any]],
) -> None:
    for override in overrides:
        if not isinstance(override, dict):
            raise ValueError("Each override must be an object")
        if override.get("disabled") is True or override.get("enabled") is False:
            continue
        for expanded in _expand_override_targets(override):
            _apply_dial_override(data, expanded)


def _iter_transition_targets(data: Dict[str, Any]):
    states = data.get("State", {})
    if not isinstance(states, dict):
        raise ValueError("Config.State must be an object")
    for state_name, state in states.items():
        transitions = state.get("Transitions", {})
        if not isinstance(transitions, dict):
            continue
        for transition_name, transition in transitions.items():
            detail = transition.get("Detail")
            if isinstance(detail, dict):
                for detail_name, detail_transition in detail.items():
                    yield state_name, transition_name, detail_name, detail_transition
            else:
                yield state_name, transition_name, None, transition


def _extract_model_detail(target: Any) -> Optional[str]:
    if not isinstance(target, dict):
        return None
    detail = target.get("Detail")
    return detail if isinstance(detail, str) else None


def _is_cohort_shock(shock: Any) -> bool:
    return isinstance(shock, dict) and (shock.get("HasCohort") is True or "Cohorts" in shock)


def _parse_dial_value(detail: Any, default: float) -> float:
    if not isinstance(detail, str):
        return default
    match = re.match(r"\s*([0-9]+(?:\.[0-9]+)?)x\b", detail)
    if not match:
        return default
    return float(match.group(1))


def _extract_root_version(data: Dict[str, Any]) -> Optional[str]:
    if not isinstance(data, dict):
        return None
    key = data.get("Key")
    if isinstance(key, dict):
        version = key.get("Version")
        if isinstance(version, str):
            return version
    version = data.get("Version")
    if isinstance(version, str):
        return version
    return None


def _default_output_path(input_path: Path, version: Optional[str]) -> Path:
    if version:
        replaced = _replace_version_in_filename(input_path.name, version)
        if replaced is not None:
            return input_path.with_name(replaced)
        return input_path.with_name(f"{input_path.stem}_{version}{input_path.suffix}")
    return input_path.with_name(f"{input_path.stem}_dial_all_example.json")


def _compact_single_target_overrides(overrides: List[Dict[str, Any]]) -> None:
    for override in overrides:
        if "targets" in override or "target" in override:
            continue
        state = override.get("state")
        transition = override.get("transition")
        if not state or not transition:
            continue
        detail = override.get("detail")
        override["target"] = _format_target_shorthand(state, transition, detail)
        override.pop("state", None)
        override.pop("transition", None)
        if detail is not None:
            override.pop("detail", None)


def generate_all_transition_overrides(
    data: Dict[str, Any],
    default_start_date: str,
    default_dial: float,
    group_by_model_detail: bool = False,
    only_with_shock: bool = False,
    compact_targets: bool = True,
) -> List[Dict[str, Any]]:
    overrides: List[Dict[str, Any]] = []
    for state, transition, detail_name, target in _iter_transition_targets(data):
        shock = target.get("Shock") if isinstance(target, dict) else None
        if only_with_shock and not isinstance(shock, dict):
            continue
        model_detail = _extract_model_detail(target)

        if _is_cohort_shock(shock):
            cohorts = shock.get("Cohorts") if isinstance(shock, dict) else None
            if not isinstance(cohorts, list) or not cohorts:
                override: Dict[str, Any] = {
                    "state": state,
                    "transition": transition,
                    "cohort": "COHORT_NAME",
                    "start_date": default_start_date,
                    "dial": default_dial,
                }
                if detail_name is not None:
                    override["detail"] = detail_name
                overrides.append(override)
                continue

            for cohort_entry in cohorts:
                if not isinstance(cohort_entry, dict):
                    continue
                cohort_name = cohort_entry.get("Cohort") or "COHORT_NAME"
                start_date = cohort_entry.get("StartDate") or default_start_date
                dial_value = _parse_dial_value(cohort_entry.get("Detail"), default_dial)
                if _is_identity_dial(dial_value):
                    continue

                override = {
                    "state": state,
                    "transition": transition,
                    "cohort": cohort_name,
                    "start_date": start_date,
                    "dial": dial_value,
                }
                if detail_name is not None:
                    override["detail"] = detail_name
                if model_detail is not None:
                    override["_model_detail"] = model_detail
                overrides.append(override)
        else:
            start_date = default_start_date
            dial_value = default_dial
            if isinstance(shock, dict):
                start_date = shock.get("StartDate") or start_date
                dial_value = _parse_dial_value(shock.get("Detail"), dial_value)
            if _is_identity_dial(dial_value):
                continue

            override = {
                "state": state,
                "transition": transition,
                "start_date": start_date,
                "dial": dial_value,
            }
            if detail_name is not None:
                override["detail"] = detail_name
            if model_detail is not None:
                override["_model_detail"] = model_detail
            overrides.append(override)

    if not group_by_model_detail:
        for override in overrides:
            override.pop("_model_detail", None)
        result = overrides
    else:
        result = _group_overrides_by_model_detail(overrides, compact_targets=compact_targets)

    if compact_targets:
        _compact_single_target_overrides(result)

    return result


def _group_overrides_by_model_detail(
    overrides: List[Dict[str, Any]],
    compact_targets: bool = True,
) -> List[Dict[str, Any]]:
    sequence: List[tuple[str, Any]] = []
    groups: Dict[tuple, Dict[str, Any]] = {}

    for override in overrides:
        model_detail = override.pop("_model_detail", None)
        if model_detail is None:
            sequence.append(("single", override))
            continue

        key = (
            model_detail,
            override.get("cohort"),
            override.get("start_date"),
            override.get("dial"),
        )
        if key not in groups:
            groups[key] = {"model_detail": model_detail, "entries": []}
            sequence.append(("group", key))
        groups[key]["entries"].append(override)

    result: List[Dict[str, Any]] = []
    for kind, payload in sequence:
        if kind == "single":
            result.append(payload)
            continue

        group = groups[payload]
        entries = group["entries"]
        if len(entries) == 1:
            result.append(entries[0])
            continue

        base = entries[0]
        grouped_override: Dict[str, Any] = {
            "model_detail": group["model_detail"],
            "targets": [],
        }
        for entry in entries:
            if compact_targets:
                grouped_override["targets"].append(
                    _format_target_shorthand(
                        entry["state"], entry["transition"], entry.get("detail")
                    )
                )
            else:
                target = {"state": entry["state"], "transition": entry["transition"]}
                if entry.get("detail") is not None:
                    target["detail"] = entry["detail"]
                grouped_override["targets"].append(target)

        for key in ("cohort", "start_date", "dial"):
            if key in base:
                grouped_override[key] = base[key]

        result.append(grouped_override)

    return result


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _order_spec_fields(spec: Dict[str, Any]) -> List[tuple[str, Any]]:
    ordered: Dict[str, Any] = {}
    for key in ("input", "output", "overrides", "version"):
        if key in spec:
            ordered[key] = spec[key]
    for key, value in spec.items():
        if key not in ordered:
            ordered[key] = value
    return list(ordered.items())


def save_spec_json(spec: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    items = _order_spec_fields(spec)
    lines: List[str] = ["{"]

    def _dump_value(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, separators=(",", ": "))

    for idx, (key, value) in enumerate(items):
        trailing = "," if idx < len(items) - 1 else ""
        if key == "overrides" and isinstance(value, list):
            lines.append(f'    "{key}": [')
            for item_idx, override in enumerate(value):
                override_suffix = "," if item_idx < len(value) - 1 else ""
                lines.append(f"        {_dump_value(override)}{override_suffix}")
            lines.append(f"    ]{trailing}")
        else:
            lines.append(f'    "{key}": {_dump_value(value)}{trailing}')

    lines.append("}")
    with path.open("w", encoding="utf-8") as file:
        file.write("\n".join(lines))


def save_json(data: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)


def _resolve_spec(spec: Any, model: Optional[str]) -> Any:
    if isinstance(spec, dict) and "models" in spec:
        models = spec["models"]
        if not isinstance(models, dict) or not models:
            raise ValueError("spec.models must be a non-empty object")
        if model is None:
            if len(models) == 1:
                model = next(iter(models.keys()))
            else:
                available = ", ".join(sorted(models.keys()))
                raise ValueError(f"Spec has multiple models. Use --model. Available: {available}")
        if model not in models:
            available = ", ".join(sorted(models.keys()))
            raise KeyError(f"Unknown model '{model}'. Available: {available}")
        return models[model]
    return spec


def _resolve_run_config(
    args: argparse.Namespace,
) -> tuple[Path, Optional[Path], Optional[str], List[Dict[str, Any]]]:
    overrides: Any = []
    input_path = DEFAULT_INPUT
    output_path = DEFAULT_OUTPUT
    version = DEFAULT_VERSION

    if args.spec is None:
        raise ValueError("Spec is required. Provide --spec to run updates.")

    spec = load_json(args.spec)
    spec = _resolve_spec(spec, args.model)
    if isinstance(spec, list):
        overrides = spec
    elif isinstance(spec, dict):
        overrides = spec.get("overrides", overrides)
        if spec.get("input") is not None:
            input_path = Path(spec["input"])
        if spec.get("output") is not None:
            output_path = Path(spec["output"])
        if spec.get("version") is not None:
            version = spec["version"]
    else:
        raise ValueError("Spec must be a list or an object")

    if args.input is not None:
        input_path = args.input
    if args.output is not None:
        output_path = args.output
    if args.version is not None:
        version = args.version

    if not isinstance(overrides, list):
        raise ValueError("Overrides must be a list")
    if not overrides:
        raise ValueError("Spec overrides is empty. Add entries before running.")

    return input_path, output_path, version, overrides


def _resolve_generate_config(args: argparse.Namespace) -> tuple[Path, Optional[Path], Optional[str]]:
    input_path = DEFAULT_INPUT
    output_path: Optional[Path] = None
    version: Optional[str] = None

    if args.spec is not None:
        spec = load_json(args.spec)
        spec = _resolve_spec(spec, args.model)
        if isinstance(spec, dict):
            if spec.get("input") is not None:
                input_path = Path(spec["input"])
            if spec.get("output") is not None:
                output_path = Path(spec["output"])
            if spec.get("version") is not None:
                version = spec["version"]
        elif not isinstance(spec, list):
            raise ValueError("Spec must be a list or an object")

    if args.input is not None:
        input_path = args.input
    if args.output is not None:
        output_path = args.output
    if args.version is not None:
        version = args.version

    return input_path, output_path, version


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply dial shocks and bump Version fields in a model config."
    )
    parser.add_argument("--spec", type=Path, default=None, help="Path to JSON spec or overrides file")
    parser.add_argument("--model", type=str, default=None, help="Model key within spec.models")
    parser.add_argument("--generate-spec", type=Path, default=None, help="Write a spec covering all transitions")
    parser.add_argument(
        "--generate-group-by-model",
        action="store_true",
        help="Group generated overrides by shared model detail file",
    )
    parser.add_argument(
        "--generate-verbose-targets",
        action="store_true",
        help="Use expanded target objects instead of shorthand",
    )
    parser.add_argument(
        "--generate-only-dials",
        action="store_true",
        help="Only include transitions that already have a Shock entry",
    )
    parser.add_argument("--generate-default-start", type=str, default="20240101")
    parser.add_argument("--generate-default-dial", type=float, default=1.0)
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--version", type=str, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.generate_spec is not None:
        input_path, output_path, version = _resolve_generate_config(args)
        data = load_json(input_path)
        if version is None:
            base_version = _extract_root_version(data)
            if base_version is None:
                raise ValueError("Unable to infer version. Provide --version.")
            version = _bump_version_string(base_version)
        if output_path is None:
            output_path = _default_output_path(input_path, version)

        overrides = generate_all_transition_overrides(
            data,
            default_start_date=args.generate_default_start,
            default_dial=args.generate_default_dial,
            group_by_model_detail=args.generate_group_by_model,
            only_with_shock=args.generate_only_dials,
            compact_targets=not args.generate_verbose_targets,
        )
        spec: Dict[str, Any] = {
            "input": str(input_path),
            "output": str(output_path),
            "overrides": overrides,
        }
        if version is not None:
            spec["version"] = version
        save_spec_json(spec, args.generate_spec)
        print(f"Wrote {args.generate_spec}")
        return 0

    input_path, output_path, version, overrides = _resolve_run_config(args)
    data = load_json(input_path)
    if version is None:
        base_version = _extract_root_version(data)
        if base_version is None:
            raise ValueError("Unable to infer version. Provide --version.")
        version = _bump_version_string(base_version)
    if output_path is None:
        output_path = _default_output_path(input_path, version)
    apply_dial_overrides(data, overrides)
    update_all_versions(data, version)
    save_json(data, output_path)
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
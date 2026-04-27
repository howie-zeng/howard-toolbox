"""JSON model curve editing utilities for the smooth notebook workflow.

Treats source model JSONs (e.g. on the N drive) as read-only, copies them to a
local baseline once, and writes edits as new JSON files alongside the baseline.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Iterator

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.interpolate import CubicSpline, PchipInterpolator, interp1d

PROTECTED_DRIVES: tuple[str, ...] = ("N:",)
EDITED_TAG: str = ".smooth_edit"


class ProtectedPathError(ValueError):
    """Raised when a write would land on a protected (read-only) path."""


def is_protected_path(path: str | Path) -> bool:
    drive = Path(path).drive.upper()
    return bool(drive) and drive in PROTECTED_DRIVES


def edited_output_path(local_baseline: str | Path) -> Path:
    """Default edited-output path next to the local baseline.

    `model.json` -> `model.smooth_edit.json`.
    """
    baseline = Path(local_baseline)
    return baseline.with_name(f"{baseline.stem}{EDITED_TAG}{baseline.suffix}")


def next_available_path(path: str | Path) -> Path:
    """Return path itself when missing; otherwise an unused suffixed sibling.

    Sequence: `foo.smooth_edit.json` -> `foo.smooth_edit_001.json` -> `_002` -> ...
    """
    output_path = Path(path)
    if not output_path.exists():
        return output_path

    for index in range(1, 1000):
        candidate = output_path.with_name(
            f"{output_path.stem}_{index:03d}{output_path.suffix}"
        )
        if not candidate.exists():
            return candidate

    raise FileExistsError(f"No unused output path found for {output_path}")


def ensure_local_model_copy(source_path: str | Path, local_path: str | Path) -> Path:
    """Copy source -> local_path on first call; reuse the existing local copy after."""
    source = Path(source_path)
    local = Path(local_path)

    if not local.exists():
        local.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, local)
        print(f"Copied source model to local baseline: {local}")
    else:
        print(f"Using existing local baseline copy: {local}")

    return local


def read_model_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


def write_model_json(
    model: dict[str, Any],
    path: str | Path,
    overwrite: bool = False,
    allow_protected: bool = False,
) -> Path:
    """Write `model` JSON to disk safely.

    Refuses protected (e.g. N-drive) destinations unless `allow_protected=True`.
    Auto-suffixes the filename so existing files are never overwritten unless
    `overwrite=True`.
    """
    output_path = Path(path)

    if not allow_protected and is_protected_path(output_path):
        raise ProtectedPathError(
            f"Refusing to write to protected path: {output_path}. "
            "Pass allow_protected=True only if you really mean to write to a read-only source."
        )

    if not overwrite:
        output_path = next_available_path(output_path)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(model, file, indent=2)
        file.write("\n")

    return output_path


def iter_curves(model: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Yield each editable curve (simple or interaction variant) in `model`."""
    for curve in model["curves"].get("simple", []):
        yield {
            "group": "simple",
            "name": curve["name"],
            "selector_field": None,
            "selector_value": None,
            "curve": curve,
        }

    for interaction in model["curves"].get("interactions", []):
        for variant in interaction["variants"]:
            yield {
                "group": "interaction",
                "name": interaction["name"],
                "selector_field": interaction["selector_field"],
                "selector_value": variant["selector_value"],
                "curve": variant,
            }


def list_curves(model: dict[str, Any], contains: str | None = None) -> pd.DataFrame:
    """Return a DataFrame summary of every curve in `model`, optionally filtered by name."""
    rows = []
    for item in iter_curves(model):
        curve = item["curve"]
        rows.append(
            {
                "group": item["group"],
                "name": item["name"],
                "selector_field": item["selector_field"],
                "selector_value": item["selector_value"],
                "n_points": curve.get("n_points", len(curve["x"])),
                "x_min": curve.get("x_min", min(curve["x"])),
                "x_max": curve.get("x_max", max(curve["x"])),
                "y_min": min(curve["y"]),
                "y_max": max(curve["y"]),
            }
        )

    df = pd.DataFrame(rows)
    if contains is not None:
        df = df[df["name"].str.contains(contains, case=False, regex=False)]
    return df.reset_index(drop=True)


def find_curve(
    model: dict[str, Any],
    name: str,
    selector_value: str | None = None,
    group: str | None = None,
) -> dict[str, Any]:
    """Return the single curve dict matching `name` (and optional `selector_value` / `group`)."""
    matches = []
    for item in iter_curves(model):
        if item["name"] != name:
            continue
        if selector_value is not None and item["selector_value"] != selector_value:
            continue
        if group is not None and item["group"] != group:
            continue
        matches.append(item)

    if len(matches) != 1:
        available = list_curves(model, contains=name)[
            ["group", "name", "selector_field", "selector_value"]
        ]
        raise ValueError(
            f"Expected one curve match for name={name!r}, selector_value={selector_value!r}, "
            f"group={group!r}; found {len(matches)}. Available matches:\n{available}"
        )

    return matches[0]["curve"]


def curve_to_df(curve: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame({"x": curve["x"], "y": curve["y"]})


def update_curve(
    model: dict[str, Any],
    name: str,
    df_curve: pd.DataFrame,
    selector_value: str | None = None,
    group: str | None = None,
) -> dict[str, Any]:
    """Replace the matched curve's `x`, `y`, `x_min`, `x_max`, `n_points` in-place."""
    curve = find_curve(model, name=name, selector_value=selector_value, group=group)
    x = [float(value) for value in df_curve["x"]]
    y = [float(value) for value in df_curve["y"]]

    curve["x"] = x
    curve["y"] = y
    curve["x_min"] = min(x)
    curve["x_max"] = max(x)
    curve["n_points"] = len(x)
    return curve


def extract_control_points(x, y, tolerance: float = 1e-3) -> list[tuple[float, float]]:
    """Reduce a curve to control points using Ramer-Douglas-Peucker.

    Smaller `tolerance` keeps more points; larger `tolerance` returns fewer.
    """
    points = np.column_stack((np.asarray(x, dtype=float), np.asarray(y, dtype=float)))

    def rdp(segment: np.ndarray, eps: float) -> np.ndarray:
        if len(segment) < 3:
            return segment

        start = segment[0]
        end = segment[-1]
        line = end - start
        line_norm = np.linalg.norm(line)
        if line_norm == 0:
            dists = np.linalg.norm(segment - start, axis=1)
        else:
            dists = np.abs(
                line[0] * (start[1] - segment[:, 1])
                - (start[0] - segment[:, 0]) * line[1]
            ) / line_norm

        idx = int(np.argmax(dists))
        if dists[idx] > eps:
            left = rdp(segment[: idx + 1], eps)
            right = rdp(segment[idx:], eps)
            return np.vstack((left[:-1], right))
        return np.vstack((start, end))

    reduced = rdp(points, tolerance)
    return [(float(px), float(py)) for px, py in reduced]


def rebuild_curve(
    controls: list[tuple[float, float]],
    x_original=None,
    y_original=None,
    n_points: int = 100,
    method: str = "pchip",
    plot: bool = True,
    title: str | None = None,
) -> pd.DataFrame:
    """Rebuild a smooth curve from control points using the chosen interpolation."""
    controls = sorted(controls, key=lambda point: point[0])
    x_ctrl, y_ctrl = map(np.array, zip(*controls))

    if method == "linear":
        interpolator = interp1d(x_ctrl, y_ctrl, kind="linear", fill_value="extrapolate")
    elif method == "quadratic":
        interpolator = interp1d(x_ctrl, y_ctrl, kind="quadratic", fill_value="extrapolate")
    elif method == "pchip":
        interpolator = PchipInterpolator(x_ctrl, y_ctrl, extrapolate=True)
    elif method == "cubic":
        interpolator = CubicSpline(x_ctrl, y_ctrl, bc_type="natural", extrapolate=True)
    else:
        raise ValueError("method must be 'linear', 'quadratic', 'pchip', or 'cubic'")

    x_new = np.linspace(float(x_ctrl.min()), float(x_ctrl.max()), n_points)
    y_new = interpolator(x_new)
    df_out = pd.DataFrame({"x": x_new, "y": y_new})

    if plot:
        plt.figure(figsize=(9, 6))
        if x_original is not None and y_original is not None:
            plt.plot(
                x_original,
                y_original,
                color="blue",
                linewidth=2.2,
                alpha=0.9,
                label="Original curve",
            )
        plt.scatter(x_ctrl, y_ctrl, c="black", edgecolor="white", label="Control points")
        plt.plot(
            x_new, y_new, "--", color="red", linewidth=2, alpha=0.85, label="Rebuilt curve"
        )
        plt.xlabel("x", fontsize=12)
        plt.ylabel("y", fontsize=12)
        plt.title(
            title if title else "Curve Replacement vs Original",
            fontsize=14,
            weight="bold",
        )
        plt.legend(frameon=True, fontsize=10, loc="best")
        plt.grid(True, linestyle="--", alpha=0.6)
        plt.tight_layout()
        plt.show()

    return df_out

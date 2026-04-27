"""GAM model dumping — calls R subprocess to convert GAM .RData to coef files."""
from __future__ import annotations

import os
import subprocess
from typing import Any, Dict, List, Optional


def _resolve_gam_paths(
    from_states: List[Dict], model_base: str,
) -> List[Dict]:
    resolved = []
    for entry in from_states:
        r = {
            "from_status": entry["from_status"],
            "output_file": entry["output_file"],
            "models": [],
        }
        for m in entry["models"]:
            path = m["path"]
            if not os.path.isabs(path):
                path = os.path.join(model_base, path)
            rm = {"path": path, "to_status": m["to_status"]}
            # Resolve stacked layer paths (optional)
            stacked = m.get("stacked", [])
            if stacked:
                rm["stacked"] = [
                    os.path.join(model_base, sp) if not os.path.isabs(sp) else sp
                    for sp in stacked
                ]
            r["models"].append(rm)
        resolved.append(r)
    return resolved


def dump_gam_models(
    config: Dict[str, Any],
    config_path: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> None:
    input_dir = config.get("input_dir", "input")
    if output_dir is None:
        output_dir = os.path.join(input_dir, "coef")
    model_base = config.get("model_base", "")
    from_states = config.get("gam_models", [])
    r_script = config.get("r_script", "tools/dump_gam_to_coef.R")
    rscript_exe = config.get("rscript_exe", "Rscript")

    os.makedirs(output_dir, exist_ok=True)

    resolved = _resolve_gam_paths(from_states, model_base)

    for entry in resolved:
        from_status = entry["from_status"]
        out_file = os.path.join(output_dir, entry["output_file"])
        for m in entry["models"]:
            model_path = m["path"]
            if not os.path.isfile(model_path):
                print(f"  WARNING: model not found: {model_path}")
                continue
            for sp in m.get("stacked", []):
                if not os.path.isfile(sp):
                    print(f"  WARNING: stacked model not found: {sp}")

        cmd = [rscript_exe, r_script, out_file]
        for m in entry["models"]:
            cmd.extend([m["path"], m["to_status"]])
            # Append stacked paths with "+" prefix
            for sp in m.get("stacked", []):
                cmd.append(f"+{sp}")

        print(f"  Dumping from{from_status}: {', '.join(m['to_status'] for m in entry['models'])}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.stdout.strip():
            print(result.stdout.rstrip())
        if result.returncode != 0:
            print(f"  STDERR: {result.stderr}")
            raise RuntimeError(f"R dump failed for from{from_status}")

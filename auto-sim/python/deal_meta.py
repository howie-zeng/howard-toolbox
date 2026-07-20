"""Deal-name -> (platform, shelf, tape dir, sim config) resolution.

Discovered from the flat-file directory tree (N:/FlatFilesMonthly/Auto/
<Platform>/<Shelf>/<DEAL FOLDER>) instead of per-issuer prefix rules, so there
is no special-casing: Carvana Prime vs Near Prime (or any future split) just
falls out of where the deal folder lives on disk. Scanned once per process.
"""
from __future__ import annotations

import os
from functools import lru_cache

TAPE_ROOT = "N:/FlatFilesMonthly/Auto"
PRIME_SHELVES = {"Prime"}      # modelling shelf: everything else folds into Subprime


def _norm(name: str) -> str:
    """Normalize a deal name or tape folder name to a shared lookup key."""
    return name.replace("-", "_").replace(" ", "_").upper()


@lru_cache(maxsize=1)
def _index() -> dict:
    idx: dict = {}
    if not os.path.isdir(TAPE_ROOT):
        return idx
    for platform in sorted(os.listdir(TAPE_ROOT)):
        pdir = os.path.join(TAPE_ROOT, platform)
        if not os.path.isdir(pdir):
            continue
        for shelf in sorted(os.listdir(pdir)):
            sdir = os.path.join(pdir, shelf)
            if not os.path.isdir(sdir):
                continue
            for folder in os.listdir(sdir):
                ddir = os.path.join(sdir, folder)
                if not os.path.isdir(ddir):
                    continue
                idx.setdefault(_norm(folder), {
                    "platform": platform,
                    "shelf": shelf,
                    "tape_dir": ddir.replace("\\", "/"),
                    "config": ("config/auto_prime.json" if shelf in PRIME_SHELVES
                               else "config/auto_subprime.json"),
                })
    return idx


def resolve(deal: str) -> dict | None:
    """Return {platform, shelf, tape_dir, config} for a deal name, or None."""
    return _index().get(_norm(deal))

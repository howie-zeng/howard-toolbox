"""Grade-aware sort key.

Handles single-letter grades (A, B), repeated-letter tiers (AAA, AA),
and prefixed grades (PP-A, UP-AA).  Order: AAA < AA < A < B < BB < C ...
"""
from __future__ import annotations

import pandas as pd


def grade_sort_key(grade: str) -> tuple:
    """Return a sortable tuple for a single grade label.

    Examples::

        "AAA"  -> ("", "A", -3)
        "AA"   -> ("", "A", -2)
        "A"    -> ("", "A", -1)
        "B"    -> ("", "B", -1)
        "PP-AA" -> ("PP", "A", -2)
        "PP-A"  -> ("PP", "A", -1)
    """
    if pd.isna(grade) or str(grade) in {"(TOTAL)", "Grand Total", "nan"}:
        return ("", "Z", 0)

    s = str(grade).strip().upper()
    prefix, grade_part = "", s
    if "-" in s:
        prefix, _, grade_part = s.partition("-")
    if not grade_part:
        return (prefix, "Z", 0)

    base = grade_part[0]
    repeat = len(grade_part)
    if all(c == base for c in grade_part):
        return (prefix, base, -repeat)
    return (prefix, grade_part, 0)


def sort_grades(grades) -> list[str]:
    """Sort a list of grade strings using ``grade_sort_key``."""
    return sorted([str(g) for g in grades], key=grade_sort_key)

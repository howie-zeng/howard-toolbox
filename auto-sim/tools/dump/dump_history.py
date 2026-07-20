"""Dump the (history-aware) gam_models to input/coef/PRIME_BASE_HISTORY — a
separate coef version from PRIME_BASE, so the dq6_bkt-aware ctd1 can be run/compared
without disturbing the existing PRIME_BASE. Stacked from-C layer stripped (BASE),
factor interactions split, then the ctd1 aging flatten re-applied. ctco is included
because it's already in gam_models.

Usage: python tools/dump/dump_history.py [config/auto_prime.json]
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "python"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from simengine import load_config
from simengine.gam_dump import dump_gam_models
from dump_coefs import _strip_stacked, _split_interactions

CONFIG = sys.argv[1] if len(sys.argv) > 1 else "config/auto_prime.json"
OUT = "input/coef/PRIME_BASE_HISTORY"

def main():
    cfg = load_config(CONFIG)
    dump_gam_models({**cfg, "gam_models": _strip_stacked(cfg["gam_models"])}, output_dir=OUT)
    _split_interactions(OUT)
    print(f"dumped -> {OUT}")

if __name__ == "__main__":
    main()

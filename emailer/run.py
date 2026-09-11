"""Generate a fancy email from raw markdown.

Edit ``MD_CONTENT`` below and run::

    python emailer/run.py

The rendered HTML will be copied to the Windows clipboard, ready to paste
into Outlook or Gmail.

CLI flags::

    --md-file PATH      Read markdown body from a file instead of MD_CONTENT.
                        Relative image paths resolve from the file's folder.
    --preview           Open the rendered HTML in the default browser.
    --no-clipboard      Render to file only; skip the clipboard copy.
    --no-resize         Embed images at original size (skip auto-resize).
"""

from __future__ import annotations

import argparse
import webbrowser
from pathlib import Path

try:
    from .render import (
        EMAILER_DIR,
        copy_to_clipboard,
        normalize_local_images,
        process_clipboard_images,
        render_markdown,
    )
except ImportError:  # running as `python emailer/run.py`
    from render import (  # type: ignore[no-redef]
        EMAILER_DIR,
        copy_to_clipboard,
        normalize_local_images,
        process_clipboard_images,
        render_markdown,
    )

OUTPUTS_DIR = EMAILER_DIR / "outputs"


# -----------------------------------------------------------------------------
# EDIT YOUR MARKDOWN CONTENT HERE
# -----------------------------------------------------------------------------
MD_CONTENT = r"""
Hi all,

Updating where the Resi deep-delinquency work stands, and splitting it into two phases so
the framework change and the model change can be judged separately.

**Phase 1 - framework only. This is what is ready now.**

Jumbo and non-FIGRE HELOC move onto the STACR framework. No new model is fitted: the
transitions being added use STACR's existing GAM files, and the dials are re-fit so
tracking error stays where it was. After this, every product except FIGRE runs the same
state machine.

| | states | transitions | GAM files identical to stacr_v1.8.2 | FCLS state |
|---|---|---|---|---|
| CRT / CAS / STACR / FNM | 14 | 85 | 85 / 85 | yes |
| MI | 14 | 85 | 83 / 85 | yes |
| NONQM | 14 | 85 | 75 / 85 | yes |
| **Jumbo** (phase 1) | 13 -> **14** | 79 -> **85** | **77 / 85** | **added** |
| **HELOC** (phase 1) | 13 -> **14** | 78 -> **85** | **75 / 85** | **added** |
| FIGRE (unchanged) | 10 | 44 | 7 / 44 | no |

*What is added.* One state, `FCLS`, and thirteen transitions - six out of it and seven into
it. Every one takes STACR's fitted GAM:

| added transition | to | GAM file |
|---|---|---|
| `FCLStoC` | C | `gam_begg_stacr_FCLStoC` |
| `FCLStoB` | M270P | `gam_begg_stacr_FCLStoB` |
| `FCLStoREO` | REO | `gam_begg_stacr_FCLStoREO` |
| `FCLStoD` | D | `gam_begg_stacr_FCLStoL` |
| `FCLStoP` | D | `gam_begg_stacr_FCLStoP` |
| `FCLStoFCLS` | FCLS | self-transition, no GAM |
| `M90toFCLS` .. `M240toFCLS` (5) | FCLS | `gam_begg_stacr_M9PtoFCLS` |
| `M270PtoFCLS` | FCLS | `gam_begg_stacr_M27PtoFCLS` |

*What is removed.* The seven `M*toDREO` transitions. A seriously delinquent loan used to
jump straight to DREO; it now routes through FCLS, which is what the tracking data actually
shows and what CRT/NQM/MI already do. HELOC additionally gains `M150toD180`.

*Why this matters beyond tidiness.* Jumbo and HELOC tapes carry FCLS loans - a single Jumbo
deal tape for 20260701 has four - and until now the engine rewrote them to M270P at
simulation start because the model had nowhere to put them. Foreclosure was invisible to
both products.

**Dials.** Re-fit so the tracking error ratio stays at one. The FCLS block is new, so it is
dialled from scratch; nothing else moves.

| transition | Jumbo v1.8.4 | 12M ratio | HELOC v1.0.V5 | 12M ratio |
|---|---|---|---|---|
| `FCLStoC` | 1.263 | 0.995 | 4.886 | 0.996 |
| `FCLStoB` | 1.481 | 0.988 | 2.104 | 0.957 |
| `FCLStoREO` | 1.940 | 1.000 | 0.100 | 1.014 |
| `FCLStoD` = `FCLStoP` | 0.743 | 0.995 | 0.462 | 0.990 |

The M60 / M90P / M270P / REO panels are untouched.

Two tracking-report definitions were wrong and are corrected in the same change, because
the FCLS dials cannot be fit against them otherwise. Both were spelling mismatches against
the data rather than modelling choices:

- The FCLS payoff fold tested `dlnq_stat_next = 'P'`. CoreLogic spells a payoff `PD`, so for
  every LP-sourced product the fold never fired and the actual side counted liquidation
  only, while the model side already carried prepay. Jumbo's real FCLS terminal flow over the
  12M window is $167.9mm; the old definition counted $11.6mm of it.
- The FCLS cure fold listed `M270`, a value that occurs nowhere. The state is `M270P`, and it
  is the modal cure target, so the largest component was dropped from both sides.

These also shift NQM's and CRT's `FCLStD` slightly, since the fold is shared.

**Phase 2 - the new deep-delinquency model.** Not in this change. Phase 1 deliberately keeps
STACR's existing coefficients so that the framework move can be reviewed on its own and the
tracking impact is near zero. Once it lands, we can swap the deep-DQ model in either way:

- *One product at a time.* Each product's tracking and risk impact is attributable to that
  product alone, and a surprise is cheap to unwind. Slower, and the products are inconsistent
  with each other while it runs.
- *All at once.* One review, one set of vectors, everything consistent from day one. But if
  something looks wrong, isolating which product caused it means re-running anyway.

My preference is one at a time, starting with NQM: it has the most FCLS history to judge
against, and it is already on the framework, so nothing else has to change alongside it.

**Not quoted here on purpose.** The vector and risk comparison I circulated earlier was run
before the two fold corrections above, so those CDR multiples and risk numbers no longer
describe what would ship. I will re-run them on the final dials and send that separately
rather than restate stale figures.

FIGRE is unchanged in both phases. It charges off at D180 so it has no real FCLS state, and
I would rather leave it alone until we revisit the FIGRE prepayment model.

Happy to walk through any of this.
"""

# -----------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python emailer/run.py",
        description="Render markdown to an Outlook-ready HTML email.",
    )
    parser.add_argument(
        "--md-file",
        type=Path,
        default=None,
        help="Read markdown body from PATH (relative image paths resolve from its folder).",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Open the rendered HTML in the default browser.",
    )
    parser.add_argument(
        "--no-clipboard",
        action="store_true",
        help="Skip copying HTML to the Windows clipboard (useful for CI / preview only).",
    )
    parser.add_argument(
        "--no-resize",
        action="store_true",
        help="Embed images at their original size (skip auto-resize).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.md_file is not None:
        md_path = args.md_file.expanduser().resolve()
        if not md_path.is_file():
            parser.error(f"--md-file not found: {md_path}")
        content = md_path.read_text(encoding="utf-8")
        base_dir = md_path.parent
        source_desc = str(md_path)
    else:
        content = MD_CONTENT
        base_dir = EMAILER_DIR
        source_desc = "MD_CONTENT (inline)"

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    content = process_clipboard_images(content)
    content = normalize_local_images(content, base_dir=base_dir)

    print(f"Formatting email from {source_desc} ...")
    output_path = OUTPUTS_DIR / "latest_email.html"
    html = render_markdown(
        content,
        output_path=str(output_path),
        base_path=str(EMAILER_DIR),
        resize_images=not args.no_resize,
    )

    if not args.no_clipboard:
        copy_to_clipboard(html)
        print("[OK] Copied rendered email to clipboard")
    else:
        print(f"[OK] Rendered HTML written to {output_path}")

    if args.preview:
        webbrowser.open(output_path.as_uri())
        print(f"[OK] Opened preview in browser: {output_path}")

    print("\n---------------------------------------------------------")
    if not args.no_clipboard:
        print("Done! The HTML is in your clipboard.")
        print("1. Go to Outlook/Gmail")
        print("2. Paste (Ctrl+V)")
    else:
        print(f"Output file: {output_path}")
    print("---------------------------------------------------------")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

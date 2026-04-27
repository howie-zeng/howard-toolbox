"""Behavior tests for emailer.run CLI and import semantics."""

from __future__ import annotations

import importlib
import sys
from base64 import b64decode
from pathlib import Path

import pytest

from emailer import run as run_module

REPO_ROOT = Path(__file__).resolve().parents[1]

WIN_ONLY = pytest.mark.skipif(
    sys.platform != "win32", reason="clipboard path requires win32clipboard"
)

PNG_HEADER = b"\x89PNG\r\n\x1a\n"


# -----------------------------------------------------------------------------
# Import semantics
# -----------------------------------------------------------------------------
def test_emailer_run_module_importable():
    module = importlib.import_module("emailer.run")
    assert hasattr(module, "MD_CONTENT")
    assert hasattr(module, "main")


def test_emailer_run_exposes_helpers_via_render():
    from emailer import render

    assert callable(render.normalize_local_images)
    assert callable(render.process_clipboard_images)
    assert callable(render.render_markdown)


def test_emailer_run_script_path_exists():
    script = REPO_ROOT / "emailer" / "run.py"
    assert script.is_file()


def test_emailer_run_imports_without_executing_main():
    """Importing the module must not render or touch the clipboard."""
    if "emailer.run" in sys.modules:
        del sys.modules["emailer.run"]
    importlib.import_module("emailer.run")


# -----------------------------------------------------------------------------
# CLI parser
# -----------------------------------------------------------------------------
def test_parser_defaults():
    parser = run_module._build_parser()
    args = parser.parse_args([])
    assert args.md_file is None
    assert args.preview is False
    assert args.no_clipboard is False
    assert args.no_resize is False


def test_parser_accepts_all_flags(tmp_path: Path):
    md = tmp_path / "body.md"
    md.write_text("# hi", encoding="utf-8")
    parser = run_module._build_parser()
    args = parser.parse_args(
        ["--md-file", str(md), "--preview", "--no-clipboard", "--no-resize"]
    )
    assert args.md_file == md
    assert args.preview is True
    assert args.no_clipboard is True
    assert args.no_resize is True


def test_missing_md_file_errors_with_actionable_message(tmp_path: Path, capsys):
    missing = tmp_path / "nowhere.md"
    with pytest.raises(SystemExit):
        run_module.main(["--md-file", str(missing), "--no-clipboard"])
    err = capsys.readouterr().err
    assert "--md-file" in err
    assert "nowhere.md" in err


# -----------------------------------------------------------------------------
# --no-clipboard renders to file only
# -----------------------------------------------------------------------------
def test_no_clipboard_writes_file_without_touching_clipboard(tmp_path: Path):
    md = tmp_path / "body.md"
    md.write_text("# hello world", encoding="utf-8")

    rc = run_module.main(["--md-file", str(md), "--no-clipboard"])
    assert rc == 0

    out = run_module.OUTPUTS_DIR / "latest_email.html"
    assert out.is_file()
    html = out.read_text(encoding="utf-8")
    assert "<h1" in html
    assert "hello world" in html


# -----------------------------------------------------------------------------
# --md-file image resolution
# -----------------------------------------------------------------------------
def test_md_file_relative_image_resolves_from_md_folder(tmp_path: Path):
    """Images referenced in an external markdown file must resolve from the
    markdown file's parent folder, not from emailer/."""
    md_dir = tmp_path / "drafts"
    md_dir.mkdir()

    img = md_dir / "chart.png"
    img.write_bytes(PNG_HEADER + b"\x00" * 128)

    md = md_dir / "body.md"
    md.write_text("Look:\n\n![](chart.png)\n", encoding="utf-8")

    assets_dir = REPO_ROOT / "emailer" / "assets"
    dest = assets_dir / "chart.png"
    if dest.exists():
        dest.unlink()

    try:
        rc = run_module.main(["--md-file", str(md), "--no-clipboard"])
        assert rc == 0

        # Image got copied into emailer/assets/ from the markdown's folder
        assert dest.is_file(), "chart.png should have been copied into emailer/assets/"

        out = run_module.OUTPUTS_DIR / "latest_email.html"
        html = out.read_text(encoding="utf-8")
        assert 'src="data:image/png;base64,' in html
        token = html.split('src="data:image/png;base64,', 1)[1].split('"', 1)[0]
        assert b64decode(token).startswith(PNG_HEADER)
    finally:
        if dest.exists():
            dest.unlink()


# -----------------------------------------------------------------------------
# Empty markdown file does not crash
# -----------------------------------------------------------------------------
def test_empty_md_file_renders_without_crashing(tmp_path: Path):
    md = tmp_path / "empty.md"
    md.write_text("", encoding="utf-8")
    rc = run_module.main(["--md-file", str(md), "--no-clipboard"])
    assert rc == 0


# -----------------------------------------------------------------------------
# --no-resize passes through to the renderer
# -----------------------------------------------------------------------------
def test_no_resize_cli_preserves_large_image_bytes(tmp_path: Path):
    import os
    from base64 import b64decode
    from io import BytesIO

    from PIL import Image

    img_dir = tmp_path / "note"
    img_dir.mkdir()
    img = Image.frombytes("RGB", (2000, 1000), os.urandom(2000 * 1000 * 3))
    original_path = img_dir / "wide.png"
    img.save(original_path, format="PNG", optimize=False)
    original_bytes = original_path.read_bytes()

    md = img_dir / "body.md"
    md.write_text("![](wide.png)\n", encoding="utf-8")

    assets_dir = REPO_ROOT / "emailer" / "assets"
    dest = assets_dir / "wide.png"
    if dest.exists():
        dest.unlink()

    try:
        rc = run_module.main(
            ["--md-file", str(md), "--no-clipboard", "--no-resize"]
        )
        assert rc == 0

        out = run_module.OUTPUTS_DIR / "latest_email.html"
        html = out.read_text(encoding="utf-8")
        token = html.split('src="data:image/png;base64,', 1)[1].split('"', 1)[0]
        embedded = b64decode(token)

        with Image.open(BytesIO(embedded)) as unchanged:
            assert unchanged.size == (2000, 1000)
        assert embedded == original_bytes
    finally:
        if dest.exists():
            dest.unlink()

"""Baseline behavior tests for emailer.render.

These tests lock in current renderer behavior before the emailer cleanup
refactor so regressions are caught at each step.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from emailer import render as render_module
from emailer.render import (
    _ensure_blank_lines_around_image_lines,
    _preprocess_math,
    maybe_resize_image_bytes,
    render_markdown,
)

WIN_ONLY = pytest.mark.skipif(
    sys.platform != "win32", reason="clipboard path requires win32clipboard"
)


def test_standalone_image_line_gets_blank_lines_before_and_after():
    src = "Hello text\n![](a.png)\nMore text"
    out = _ensure_blank_lines_around_image_lines(src)
    lines = out.splitlines()
    idx = lines.index("![](a.png)")
    assert lines[idx - 1] == ""
    assert lines[idx + 1] == ""


def test_inline_image_in_text_is_not_separated():
    src = "Before ![](a.png) After"
    out = _ensure_blank_lines_around_image_lines(src)
    assert out == "Before ![](a.png) After"


def test_fenced_code_block_image_line_is_untouched():
    src = "```\n![](a.png)\n```"
    out = _ensure_blank_lines_around_image_lines(src)
    assert out == src


def test_render_markdown_basic_smoke(tmp_path: Path):
    html = render_markdown("**bold** text", base_path=str(tmp_path))
    assert "<strong>bold</strong>" in html
    assert "font-family" in html


def test_render_markdown_table_produces_table_tag(tmp_path: Path):
    md = "| A | B |\n|---|---|\n| 1 | 2 |\n"
    html = render_markdown(md, base_path=str(tmp_path))
    assert "<table" in html
    assert "<th" in html
    assert "<td" in html


def test_render_markdown_missing_image_does_not_crash(tmp_path: Path, capsys):
    md = "![](does_not_exist.png)"
    html = render_markdown(md, base_path=str(tmp_path))
    out = capsys.readouterr().out
    assert "does_not_exist.png" in out
    assert "<img" in html


def test_render_markdown_embeds_existing_image_as_base64(tmp_path: Path):
    from base64 import b64decode

    png_header = b"\x89PNG\r\n\x1a\n"
    img_path = tmp_path / "tiny.png"
    img_path.write_bytes(png_header + b"\x00" * 64)

    html = render_markdown("![](tiny.png)", base_path=str(tmp_path))

    assert 'src="data:image/png;base64,' in html
    token = html.split('src="data:image/png;base64,', 1)[1].split('"', 1)[0]
    assert b64decode(token).startswith(png_header)


def test_math_inline_becomes_codecogs_image():
    out = _preprocess_math("The error is $\\epsilon$.")
    assert "latex.codecogs.com" in out
    assert "<img" in out


def test_math_inside_fenced_code_is_preserved():
    src = "```\nx = $a$\n```"
    out = _preprocess_math(src)
    assert out == src


def test_math_inside_inline_code_is_preserved():
    src = "use `$a$` for inline math"
    out = _preprocess_math(src)
    assert out == src


def test_render_module_exposes_public_api():
    assert hasattr(render_module, "render_markdown")
    assert hasattr(render_module, "copy_to_clipboard")


def test_default_container_uses_outlook_friendly_font_stack(tmp_path: Path):
    html = render_markdown("hello", base_path=str(tmp_path))
    # Default stack should prefer Outlook-native sans before falling back.
    assert "Aptos" in html
    assert "Calibri" in html
    assert "Times New Roman" not in html


@WIN_ONLY
def test_copy_to_clipboard_callable_on_windows():
    assert callable(render_module.copy_to_clipboard)


# -----------------------------------------------------------------------------
# Image resize behavior
# -----------------------------------------------------------------------------
def _make_png_bytes(width: int, height: int) -> bytes:
    """Create a noise PNG that does NOT compress trivially, so length checks
    reflect real resize savings."""
    import io
    import os

    from PIL import Image

    img = Image.frombytes("RGB", (width, height), os.urandom(width * height * 3))
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=False)
    return buf.getvalue()


def test_resize_downscales_large_dimensions():
    from io import BytesIO

    from PIL import Image

    data = _make_png_bytes(2000, 1000)
    new_data, did_resize = maybe_resize_image_bytes(data, max_long_edge=1600)

    assert did_resize is True
    assert len(new_data) < len(data)

    with Image.open(BytesIO(new_data)) as resized:
        assert max(resized.size) == 1600
        # Aspect ratio preserved (tolerance for integer rounding)
        assert abs(resized.size[0] / resized.size[1] - 2.0) < 0.01


def test_resize_leaves_small_image_untouched():
    data = _make_png_bytes(200, 200)
    new_data, did_resize = maybe_resize_image_bytes(data, max_long_edge=1600)
    assert did_resize is False
    assert new_data == data


def test_resize_preserves_aspect_ratio_portrait():
    from io import BytesIO

    from PIL import Image

    data = _make_png_bytes(800, 2400)
    new_data, did_resize = maybe_resize_image_bytes(data, max_long_edge=1200)

    assert did_resize is True
    with Image.open(BytesIO(new_data)) as resized:
        assert max(resized.size) == 1200
        assert resized.size[1] > resized.size[0]


def test_resize_gracefully_handles_garbage_bytes():
    data = b"not-an-image-at-all"
    new_data, did_resize = maybe_resize_image_bytes(data)
    assert did_resize is False
    assert new_data is data


def test_render_markdown_resize_enabled_by_default(tmp_path: Path):
    from base64 import b64decode
    from io import BytesIO

    from PIL import Image

    img_path = tmp_path / "huge.png"
    img_path.write_bytes(_make_png_bytes(2000, 1000))

    html = render_markdown("![](huge.png)", base_path=str(tmp_path))

    token = html.split('src="data:image/png;base64,', 1)[1].split('"', 1)[0]
    embedded = b64decode(token)
    with Image.open(BytesIO(embedded)) as resized:
        assert max(resized.size) == 1600


def test_render_markdown_no_resize_preserves_original(tmp_path: Path):
    from base64 import b64decode
    from io import BytesIO

    from PIL import Image

    img_path = tmp_path / "huge.png"
    original = _make_png_bytes(2000, 1000)
    img_path.write_bytes(original)

    html = render_markdown(
        "![](huge.png)", base_path=str(tmp_path), resize_images=False
    )

    token = html.split('src="data:image/png;base64,', 1)[1].split('"', 1)[0]
    embedded = b64decode(token)
    assert embedded == original
    with Image.open(BytesIO(embedded)) as unchanged:
        assert unchanged.size == (2000, 1000)

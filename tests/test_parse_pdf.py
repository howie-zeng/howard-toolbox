from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from emailer import parse_pdf as parse_module

PNG_HEADER = b"\x89PNG\r\n\x1a\n"


def _sample_pdf(path: Path) -> Path:
    doc = fitz.open()
    coef_page = doc.new_page(width=800, height=600)
    coef_page.insert_text((72, 72), "Parametric coefficients", fontsize=12)
    y = 140
    for x, text in (
        (72, "judflgNY"),
        (200, "-2.91"),
        (320, "0.12"),
        (440, "-24.2"),
        (540, "<2e-16"),
        (620, "***"),
    ):
        coef_page.insert_text((x, y), text, fontsize=10)

    smooth_page = doc.new_page(width=800, height=600)
    smooth_page.insert_text((72, 72), "Approximate significance of smooth terms", fontsize=12)
    for x, text in ((72, "s(c_cltv)"), (200, "8.21"), (320, "9.10")):
        smooth_page.insert_text((x, 120), text, fontsize=10)

    doc.save(path)
    doc.close()
    return path


def test_parse_pages_one_based() -> None:
    assert parse_module.parse_pages("2,4-6") == [1, 3, 4, 5]
    with pytest.raises(ValueError):
        parse_module.parse_pages("0")


def test_normalize_minus_strips_unicode_minus() -> None:
    assert parse_module.normalize_minus("−2.91") == "-2.91"
    assert parse_module.normalize_minus("1,234.5") == "1234.5"


def test_parse_coef_and_smooths(tmp_path: Path) -> None:
    pdf = _sample_pdf(tmp_path / "report.pdf")
    doc = fitz.open(str(pdf))
    try:
        coefs = parse_module.parse_coef_page(doc[0])
        smooths = parse_module.parse_smooths(doc[1])
    finally:
        doc.close()

    assert coefs[0]["term"] == "judflgNY"
    assert coefs[0]["est"] == "-2.91"
    assert smooths[0][0] == "s(c_cltv)"


def test_render_pages_uses_names(tmp_path: Path) -> None:
    pdf = _sample_pdf(tmp_path / "report.pdf")
    written = parse_module.render_pages(
        pdf,
        [0, 1],
        tmp_path / "out",
        prefix="FCLStoREO",
        names=["smooth", "overtime"],
    )

    assert [path.name for path in written] == ["FCLStoREO_smooth.png", "FCLStoREO_overtime.png"]
    assert written[0].read_bytes()[:8] == PNG_HEADER


def test_cli_coefs_and_info(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    pdf = _sample_pdf(tmp_path / "report.pdf")
    csv_path = tmp_path / "coefs.csv"

    assert parse_module.main(["coefs", "--pdf", str(pdf), "--page", "1", "--out", str(csv_path)]) == 0
    text = csv_path.read_text(encoding="utf-8")
    assert "judflgNY" in text
    assert "-2.91" in text

    assert parse_module.main(["info", "--pdf", str(pdf)]) == 0
    captured = capsys.readouterr()
    assert "pages=2" in captured.out
    assert "Parametric coefficients" in captured.out

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from openpyxl import Workbook

from emailer import plot_vector_compare as plot_module


def _write_vector_workbook(path: Path) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "vectors"
    worksheet.append(["BBG Deal", "Model", "Scenario", "Date", "Month", "CPR", "CDR"])
    worksheet.append(
        [
            "VERUS 2022-1",
            "New NonQM V9 No Decay Dialed",
            "Base",
            datetime(2026, 1, 1),
            1,
            8.0,
            1.25,
        ]
    )
    workbook.save(path)
    workbook.close()


def _records_for_all_models() -> list[dict[str, object]]:
    return [
        {
            "deal": "VERUS 2022-1",
            "model": model,
            "scenario": "Base",
            "month": 1.0,
            "date": datetime(2026, 1, 1),
            "value": 1.25,
        }
        for model in plot_module.MODEL_STYLES
    ]


def test_parser_defaults_to_cpr_and_accepts_cdr() -> None:
    parser = plot_module._build_parser()

    assert parser.parse_args([]).metric == "CPR"
    assert parser.parse_args(["--metric", "CDR"]).metric == "CDR"


def test_load_data_uses_selected_metric(tmp_path: Path) -> None:
    workbook_path = tmp_path / "vectors.xlsx"
    _write_vector_workbook(workbook_path)

    records = plot_module._load_data(workbook_path, "vectors", "CDR")

    assert records[0]["value"] == 1.25


def test_plot_filename_includes_metric(tmp_path: Path) -> None:
    output_path = plot_module.plot_deal_scenario(
        _records_for_all_models(),
        "VERUS 2022-1",
        "Base",
        tmp_path,
        120,
        plot_module._models_to_plot(False),
        "CDR",
    )

    assert output_path is not None
    assert output_path.name == "verus_2022_1_cdr_base.png"


def test_plot_requires_every_requested_model(tmp_path: Path) -> None:
    records = _records_for_all_models()[:-1]

    output_path = plot_module.plot_deal_scenario(
        records,
        "VERUS 2022-1",
        "Base",
        tmp_path,
        120,
        plot_module._models_to_plot(False),
        "CPR",
    )

    assert output_path is None


def test_main_fails_for_incomplete_requested_comparison(tmp_path: Path) -> None:
    workbook_path = tmp_path / "vectors.xlsx"
    _write_vector_workbook(workbook_path)

    result = plot_module.main(
        [
            "--workbook",
            str(workbook_path),
            "--sheet",
            "vectors",
            "--output-dir",
            str(tmp_path / "plots"),
            "--deals",
            "VERUS 2022-1",
            "--scenarios",
            "Base",
        ]
    )

    assert result == 1


def test_model_styles_include_only_requested_curves() -> None:
    assert set(plot_module.MODEL_STYLES) == {
        "Prod",
        "New NonQM",
        "JPM",
        "New NonQM V9 No Decay Dialed",
    }
    assert plot_module.MODEL_STYLES["New NonQM"]["label"] == "New NQM"
    dialed_style = plot_module.MODEL_STYLES["New NonQM V9 No Decay Dialed"]
    assert dialed_style["label"] == "Dialed NQM"
    assert dialed_style["color"] == "#d4a017"

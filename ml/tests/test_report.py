"""Unit tests for the results table and chart."""
from pathlib import Path

from ml.src.report import plot_comparison, results_to_frame, save_table, to_markdown

RESULTS = {
    "full": {
        "popularity": {"precision@2": 0.1, "recall@2": 0.2, "hit_rate@2": 0.3, "n_users_evaluated": 5},
        "als": {"precision@2": 0.4, "recall@2": 0.5, "hit_rate@2": 0.6, "n_users_evaluated": 5},
    },
    "discovery": {
        "popularity": {"precision@2": 0.01, "recall@2": 0.02, "hit_rate@2": 0.03, "n_users_evaluated": 4},
        "als": {"precision@2": 0.04, "recall@2": 0.05, "hit_rate@2": 0.06, "n_users_evaluated": 4},
    },
}


def test_frame_has_one_row_per_protocol_and_model() -> None:
    frame = results_to_frame(RESULTS)
    assert len(frame) == 4
    assert list(frame.columns[:2]) == ["protocol", "model"]


def test_markdown_table_lists_every_row_with_rounded_metrics() -> None:
    lines = to_markdown(results_to_frame(RESULTS), k=2).splitlines()
    assert len(lines) == 2 + 4
    assert lines[2] == "| full | popularity | 0.1000 | 0.2000 | 0.3000 | 5 |"


def test_table_and_chart_files_are_written(tmp_path: Path) -> None:
    frame = results_to_frame(RESULTS)
    save_table(frame, 2, tmp_path)
    plot_comparison(frame, 2, tmp_path / "chart.png")
    for name in ("results_table.csv", "results_table.md", "chart.png"):
        assert (tmp_path / name).stat().st_size > 0
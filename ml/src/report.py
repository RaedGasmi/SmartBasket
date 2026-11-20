"""Turn the metrics dictionary into a results table (CSV, Markdown) and a comparison chart."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def metric_columns(k: int) -> list[str]:
    """Names of the ranking metrics in the results, in display order."""
    return [f"precision@{k}", f"recall@{k}", f"hit_rate@{k}"]


def results_to_frame(results: dict[str, dict[str, dict[str, float]]]) -> pd.DataFrame:
    """Flatten {protocol: {model: metrics}} into one row per (protocol, model)."""
    rows = [
        {"protocol": protocol, "model": model, **metrics}
        for protocol, by_model in results.items()
        for model, metrics in by_model.items()
    ]
    return pd.DataFrame(rows)


def to_markdown(frame: pd.DataFrame, k: int) -> str:
    """Render the results as a GitHub Markdown table, metrics rounded to 4 decimals."""
    columns = metric_columns(k)
    lines = [
        "| Protocol | Model | " + " | ".join(columns) + " | Users evaluated |",
        "|---|---|" + "---:|" * (len(columns) + 1),
    ]
    for row in frame.to_dict("records"):
        values = " | ".join(f"{row[column]:.4f}" for column in columns)
        lines.append(f"| {row['protocol']} | {row['model']} | {values} | {int(row['n_users_evaluated'])} |")
    return "\n".join(lines) + "\n"


def save_table(frame: pd.DataFrame, k: int, directory: Path) -> None:
    """Write results_table.csv and results_table.md into the directory."""
    frame.round(4).to_csv(directory / "results_table.csv", index=False)
    (directory / "results_table.md").write_text(to_markdown(frame, k))


def plot_comparison(frame: pd.DataFrame, k: int, path: Path) -> None:
    """Save one grouped bar chart per protocol: metrics on the x axis, one bar per model."""
    columns = metric_columns(k)
    protocols = list(frame["protocol"].unique())
    fig, axes = plt.subplots(1, len(protocols), figsize=(6.5 * len(protocols), 4.5), squeeze=False)
    for ax, protocol in zip(axes[0], protocols):
        subset = frame[frame["protocol"] == protocol].set_index("model")
        subset[columns].T.plot.bar(ax=ax, rot=0)
        ax.set(title=f"{protocol} protocol ({int(subset['n_users_evaluated'].iloc[0])} users)", ylabel="score")
        ax.legend(title="model")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
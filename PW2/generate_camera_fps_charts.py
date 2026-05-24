from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

from utils.macros import OUTPUT_STATS_DIR


DEFAULT_CSV_PATH = OUTPUT_STATS_DIR / "camera_fps" / "live_camera_fps_summary.csv"


def format_resolution(resolution: str) -> str:
    return resolution.replace("x", " x ")


def generate_camera_fps_charts(df: pd.DataFrame, output_dir: Path, resolution: str = "1920x1080") -> None:
    stat_path = output_dir / "camera_fps_charts"
    stat_path.mkdir(parents=True, exist_ok=True)

    required_columns = {"Algorithm", "Resolution", "Target Colors"}
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(f"Dataframe is missing required columns: {', '.join(sorted(missing_columns))}")

    fps_column = "Avg_FPS" if "Avg_FPS" in df.columns else "FPS"
    if fps_column not in df.columns:
        raise ValueError("Dataframe must contain either 'Avg_FPS' or 'FPS'.")

    df = df[df["Resolution"].astype(str) == resolution].copy()
    if df.empty:
        print(f"No data found for Resolution = {resolution}. Skipping.")
        return

    agg_dict: dict[str, tuple[str, str]] = {fps_column: (fps_column, "mean")}
    if "Sample_Count" in df.columns:
        agg_dict["Sample_Count"] = ("Sample_Count", "sum")

    summary_df = (
        df.groupby(["Resolution", "Target Colors", "Algorithm"], as_index=False)
        .agg(**agg_dict)
        .sort_values(["Target Colors", fps_column], ascending=[True, False])
    )

    target_order = sorted(summary_df["Target Colors"].dropna().astype(int).unique().tolist())
    algorithm_order = summary_df.groupby("Algorithm")[fps_column].mean().sort_values(ascending=False).index.tolist()
    algorithm_colors = {algorithm: plt.cm.tab10(index % 10) for index, algorithm in enumerate(algorithm_order)}

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(1, 1, figsize=(14, 7))

    group_width = 0.8
    x_positions = np.arange(len(target_order)) * 1.6
    max_bars = max(1, len(algorithm_order))
    bar_width = group_width / max_bars

    for x_position, target_color in zip(x_positions, target_order):
        color_df = summary_df[summary_df["Target Colors"] == target_color].copy()
        color_df = color_df.sort_values(fps_column, ascending=False)

        values = color_df[fps_column].tolist()
        algorithms = color_df["Algorithm"].tolist()
        total_width = bar_width * len(values)
        start = x_position - total_width / 2 + bar_width / 2

        for bar_index, (algorithm, fps_value) in enumerate(zip(algorithms, values)):
            left = start + bar_index * bar_width
            ax.bar(
                left,
                fps_value,
                width=bar_width,
                color=algorithm_colors[algorithm],
                align="center",
                edgecolor="none",
                zorder=3,
            )

    ax.set_xticks(x_positions)
    ax.set_xticklabels(target_order, rotation=0)
    ax.set_title("AVG FPS (Camera 30 fps max)", pad=15)
    ax.set_xlabel("Target Colors")
    ax.set_ylabel("Avg FPS")
    ax.grid(axis="y", linestyle="--", alpha=0.7)
    ax.grid(axis="x", visible=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.suptitle(
        f"Live Camera FPS: {format_resolution(resolution)}",
        fontsize=16,
        fontweight="bold",
        y=1.02,
    )

    legend_order = [algorithm for algorithm in algorithm_order if algorithm in algorithm_colors]
    ordered_handles = [Patch(facecolor=algorithm_colors[algorithm], label=algorithm) for algorithm in legend_order]
    fig.legend(
        ordered_handles,
        legend_order,
        loc="lower center",
        ncol=len(legend_order),
        bbox_to_anchor=(0.5, -0.03),
        frameon=False,
        handletextpad=0.5,
    )

    fig.subplots_adjust(top=0.86)

    output_file = stat_path / f"{resolution}_fps_chart.png"
    plt.savefig(output_file, bbox_inches="tight", dpi=300, facecolor="white")
    plt.close()

    print(f"Generated: {output_file.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate FPS charts from the live camera benchmark CSV")
    parser.add_argument(
        "--csv",
        type=str,
        default=str(DEFAULT_CSV_PATH),
        help="Path to the live camera FPS CSV file",
    )
    parser.add_argument(
        "--charts-dir",
        type=str,
        default=str(OUTPUT_STATS_DIR),
        help="Directory where the FPS charts will be written",
    )
    parser.add_argument(
        "--resolution",
        type=str,
        default="1920x1080",
        help="Resolution to chart",
    )

    args = parser.parse_args()

    csv_path = Path(args.csv)
    charts_dir = Path(args.charts_dir)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    df = pd.read_csv(csv_path)
    generate_camera_fps_charts(df, charts_dir, resolution=args.resolution)
    print("--- Camera FPS analysis completed successfully ---")


if __name__ == "__main__":
    main()
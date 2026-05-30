from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.macros import OUTPUT_STATS_DIR


def format_image_name(image_name: str) -> str:
    if image_name.lower().startswith("woods_"):
        suffix = image_name.split("_", 1)[1]
        return f"Woods {suffix}"
    return image_name.replace("_", " ").title()


def calculate_tradeoff_rank(df: pd.DataFrame) -> pd.DataFrame:
    ranked_chunks = []

    group_cols = ["Target Colors"]
    if "Resolution" in df.columns:
        group_cols.insert(0, "Resolution")

    for group_keys, group in df.groupby(group_cols):
        group = group.copy()

        time_values = np.log1p(group["Time Taken (ms)"].astype(float))
        ssim_values = group["SSIM"].astype(float)

        time_min = time_values.min()
        time_range = time_values.max() - time_min
        ssim_min = ssim_values.min()
        ssim_range = ssim_values.max() - ssim_min

        time_norm = (time_values - time_min) / time_range if time_range > 0 else pd.Series(0.0, index=group.index)
        ssim_norm = (ssim_values - ssim_min) / ssim_range if ssim_range > 0 else pd.Series(1.0, index=group.index)

        distance_to_ideal = np.sqrt(time_norm**2 + (1.0 - ssim_norm)**2)

        group["Tradeoff Score"] = distance_to_ideal
        group["Rank"] = distance_to_ideal.rank(method="min").astype(int)

        ranked_chunks.append(group)

    return pd.concat(ranked_chunks, ignore_index=True)


def generate_tradeoff_charts(df: pd.DataFrame, output_dir: Path) -> None:
    """Receive an already-ranked dataframe summarized by resolution and target colors."""
    stat_path = output_dir / "tradeoff_charts"
    stat_path.mkdir(parents=True, exist_ok=True)

    if df.empty:
        print("Warning: No data to chart. Skipping.")
        return

    ranked_df = df

    has_resolution = "Resolution" in ranked_df.columns
    if has_resolution:
        resolution_order = ranked_df["Resolution"].dropna().astype(str).unique().tolist()
    else:
        resolution_order = [None]

    print("Generating tradeoff charts...")

    for resolution in resolution_order:
        if has_resolution:
            resolution_df = ranked_df[ranked_df["Resolution"].astype(str) == resolution].copy()
        else:
            resolution_df = ranked_df.copy()

        if resolution_df.empty:
            continue

        target_order = sorted(resolution_df["Target Colors"].dropna().astype(int).unique().tolist())
        algorithm_order = (
            resolution_df.groupby("Algorithm")["Rank"].mean().sort_values(ascending=True).index.tolist()
        )
        algorithm_colors = {
            algorithm: plt.cm.tab10(index % 10)
            for index, algorithm in enumerate(algorithm_order)
        }

        plt.style.use("seaborn-v0_8-whitegrid")
        fig, ax = plt.subplots(1, 1, figsize=(14, 7))

        group_width = 0.8
        x_positions = np.arange(len(target_order)) * 1.6
        max_bars = max(1, len(algorithm_order))
        bar_width = group_width / max_bars

        for target_color, x_position in zip(target_order, x_positions):
            color_df = resolution_df[resolution_df["Target Colors"] == target_color].copy()
            color_df = color_df.sort_values(["Rank", "Algorithm"], ascending=[True, True]).reset_index(drop=True)

            values = color_df["Rank"].tolist()
            algorithms = color_df["Algorithm"].tolist()
            total_width = bar_width * len(values)
            start = x_position - total_width / 2 + bar_width / 2

            for bar_index, (algorithm, rank_value) in enumerate(zip(algorithms, values)):
                left = start + bar_index * bar_width
                ax.bar(
                    left,
                    rank_value,
                    width=bar_width,
                    color=algorithm_colors[algorithm],
                    align="center",
                    edgecolor="none",
                    label=algorithm if target_color == target_order[0] else "",
                    zorder=3,
                )

        ax.set_xticks(x_positions)
        ax.set_xticklabels(target_order, rotation=0)
        ax.set_title("Ranked by Pareto Score", pad=15)
        ax.set_xlabel("Target Colors")
        ax.set_ylabel("Rank (1 = best tradeoff)")
        ax.grid(axis="y", linestyle="--", alpha=0.7)
        ax.grid(axis="x", visible=False)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        if has_resolution:
            fig.suptitle(f"Pareto Ranking: {resolution}", fontsize=16, fontweight="bold", y=1.02)
        else:
            fig.suptitle("Pareto Ranking", fontsize=16, fontweight="bold", y=1.02)

        legend_order = [algorithm for algorithm in algorithm_order if algorithm in algorithm_colors]
        ordered_handles = [plt.Rectangle((0, 0), 1, 1, color=algorithm_colors[algorithm]) for algorithm in legend_order]
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

        safe_resolution = str(resolution).replace("/", "_") if resolution is not None else "all_resolutions"
        output_file = stat_path / f"{safe_resolution}_tradeoff_chart.png"
        plt.savefig(output_file, bbox_inches="tight", dpi=300, facecolor="white")
        plt.close()

        print(f"Generated: {output_file.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate time-vs-SSIM tradeoff charts from a benchmark CSV")
    parser.add_argument("csv", type=str, help="Path to the benchmark CSV file")
    parser.add_argument(
        "--charts-dir",
        type=str,
        default=str(OUTPUT_STATS_DIR),
        help="Directory where the tradeoff charts will be written",
    )

    args = parser.parse_args()

    csv_path = Path(args.csv)
    charts_dir = Path(args.charts_dir)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    df = pd.read_csv(csv_path)

    required_columns = {"Image Name", "Algorithm", "Time Taken (ms)", "SSIM", "Target Colors"}
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(f"CSV file '{csv_path}' is missing: {', '.join(sorted(missing_columns))}")

    df = df[df["Algorithm"] != "Shader-Acerola"].copy()

    df["Target Colors"] = pd.to_numeric(df["Target Colors"], errors="coerce")
    df = df.dropna(subset=["Target Colors"]).copy()

    if df.empty:
        print("No data found for Target Colors. Exiting.")
        return

    has_resolution = "Resolution" in df.columns
    group_cols = ["Target Colors"]
    if has_resolution:
        group_cols.insert(0, "Resolution")

    print("Aggregating data by Algorithm for all target colors and resolutions...")
    agg_df = (
        df.groupby(group_cols + ["Algorithm"], as_index=False)
        .agg(
            **{
                "Time Taken (ms)": ("Time Taken (ms)", "mean"),
                "SSIM": ("SSIM", "mean"),
            }
        )
    )

    print("Calculating Tradeoff Ranks...")
    ranked_df = calculate_tradeoff_rank(agg_df)
    ranked_df = ranked_df.sort_values(by=group_cols + ["Rank"])

    output_csv_path = charts_dir / "ranked_benchmarks.csv"
    charts_dir.mkdir(parents=True, exist_ok=True)
    ranked_df.to_csv(output_csv_path, index=False)
    print(f"Saved ranked data to: {output_csv_path}")

    generate_tradeoff_charts(ranked_df, charts_dir)
    print("--- Tradeoff analysis completed successfully ---")


if __name__ == "__main__":
    main()
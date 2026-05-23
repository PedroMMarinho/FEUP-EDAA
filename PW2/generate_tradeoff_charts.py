from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np
import pandas as pd
from adjustText import adjust_text

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.macros import OUTPUT_STATS_DIR


def format_image_name(image_name: str) -> str:
    if image_name.lower().startswith("woods_"):
        suffix = image_name.split("_", 1)[1]
        return f"Woods {suffix}"
    return image_name.replace("_", " ").title()


def pareto_frontier(df: pd.DataFrame) -> pd.DataFrame:
    # Sort by Time (ascending/better) and SSIM (descending/better)
    ordered = df.sort_values(["Time Taken (ms)", "SSIM"], ascending=[True, False]).reset_index(drop=True)

    frontier_indices: list[int] = []
    best_ssim = -np.inf
    for index, row in ordered.iterrows():
        if row["SSIM"] > best_ssim:
            frontier_indices.append(index)
            best_ssim = row["SSIM"]

    return ordered.loc[frontier_indices].copy()


def compute_best_tradeoff(df: pd.DataFrame) -> pd.Series:
    time_values = np.log1p(df["Time Taken (ms)"].astype(float)) 
    ssim_values = df["SSIM"].astype(float)

    time_min = time_values.min()
    time_range = time_values.max() - time_min
    ssim_min = ssim_values.min()
    ssim_range = ssim_values.max() - ssim_min

    time_norm = (time_values - time_min) / time_range if time_range > 0 else pd.Series(0.0, index=df.index)
    ssim_norm = (ssim_values - ssim_min) / ssim_range if ssim_range > 0 else pd.Series(1.0, index=df.index)

    ideal_distance = np.sqrt(time_norm**2 + (1.0 - ssim_norm)**2)
    best_index = ideal_distance.idxmin()
    return df.loc[best_index]


def generate_tradeoff_charts(df: pd.DataFrame, output_dir: Path) -> None:
    stat_path = output_dir / "tradeoff_charts"
    stat_path.mkdir(parents=True, exist_ok=True)

    df = df[df["Algorithm"] != "Shader-Acerola"].copy()
    unique_images = df["Image Name"].dropna().unique()
    print(f"Found {len(unique_images)} unique images. Generating tradeoff charts...")

    for image_name in unique_images:
        image_df = df[df["Image Name"] == image_name].copy()
        image_df = image_df.dropna(subset=["Time Taken (ms)", "SSIM"])

        if image_df.empty:
            continue

        summary_df = (
            image_df.groupby("Algorithm", as_index=False)
            .agg(
                **{
                    "Time Taken (ms)": ("Time Taken (ms)", "mean"),
                    "SSIM": ("SSIM", "mean"),
                }
            )
        )

        frontier_df = pareto_frontier(summary_df)
        best_row = compute_best_tradeoff(summary_df)

        plt.style.use("seaborn-v0_8-whitegrid")
        fig, ax = plt.subplots(1, 1, figsize=(12, 8))

        unique_algs = summary_df["Algorithm"].unique()
        color_palette = cm.get_cmap('tab20')(np.linspace(0, 1, len(unique_algs)))
        color_map = dict(zip(unique_algs, color_palette))
        point_colors = [color_map[alg] for alg in summary_df["Algorithm"]]

        ax.scatter(
            summary_df["Time Taken (ms)"],
            summary_df["SSIM"],
            s=130,
            c=point_colors,
            alpha=0.9,
            edgecolor="white",
            linewidth=1,
            zorder=3,
        )

        if len(frontier_df) > 1:
            ax.plot(
                frontier_df["Time Taken (ms)"],
                frontier_df["SSIM"],
                color="#2563eb", 
                linewidth=2.0,
                linestyle="--",
                zorder=2, # Draw the line behind the colored points
                label="Pareto Frontier",
            )

        ax.scatter(
            best_row["Time Taken (ms)"],
            best_row["SSIM"],
            s=450, 
            marker="*",
            facecolors='none', 
            edgecolor="black",
            linewidth=1.5,
            zorder=4,
            label=f"Best Overall ({best_row['Algorithm']})",
        )

        texts = []
        for _, row in summary_df.iterrows():
            is_best = row['Algorithm'] == best_row['Algorithm']
            texts.append(
                ax.text(
                    row["Time Taken (ms)"], 
                    row["SSIM"], 
                    row["Algorithm"],
                    fontsize=10 if not is_best else 12,
                    fontweight='bold' if is_best else 'normal',
                    color="#1f2937",
                    zorder=5
                )
            )
            
        adjust_text(
            texts, 
            expand_points=(1.8, 1.8),
        )

        ax.set_xscale("log")
        ax.set_xlabel("Avg Time Taken (ms)", fontsize=12, fontweight='medium')
        ax.set_ylabel("Avg SSIM", fontsize=12, fontweight='medium')
        ax.grid(True, which="major", axis="both", linestyle="-", alpha=0.4)
        ax.grid(True, which="minor", axis="x", linestyle=":", alpha=0.2)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        display_name = format_image_name(str(image_name))
        fig.suptitle(f"Algorithm Tradeoff: {display_name}", fontsize=16, fontweight="bold", y=0.96)

        legend = ax.legend(loc="lower right", frameon=True, fontsize=10)
        legend.get_frame().set_alpha(0.9)
        legend.get_frame().set_edgecolor('#e5e7eb')

        fig.tight_layout()

        safe_name = Path(str(image_name)).stem
        output_file = stat_path / f"{safe_name}_tradeoff_chart.png"
        plt.savefig(output_file, bbox_inches="tight", dpi=300, facecolor='white')
        plt.close()

        print(f"Generated: {output_file.name} | Best tradeoff: {best_row['Algorithm']}")


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

    required_columns = {"Image Name", "Algorithm", "Time Taken (ms)", "SSIM"}
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(f"CSV file '{csv_path}' is missing: {', '.join(sorted(missing_columns))}")

    generate_tradeoff_charts(df, charts_dir)
    print("--- Tradeoff analysis completed successfully ---")


if __name__ == "__main__":
    main()
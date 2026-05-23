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
    """Compute the Pareto frontier for a single (image, resolution) slice."""
    ordered = df.sort_values(["Time Taken (ms)", "SSIM"], ascending=[True, False]).reset_index(drop=True)

    frontier_indices: list[int] = []
    best_ssim = -np.inf
    for index, row in ordered.iterrows():
        if row["SSIM"] > best_ssim:
            frontier_indices.append(index)
            best_ssim = row["SSIM"]

    return ordered.loc[frontier_indices].copy()


def calculate_tradeoff_rank(df: pd.DataFrame) -> pd.DataFrame:
    ranked_chunks = []

    group_cols = ["Image Name", "Resolution"] if "Resolution" in df.columns else ["Image Name"]

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
    """Receive an already-filtered (Target Colors == 256) and ranked dataframe."""
    stat_path = output_dir / "tradeoff_charts_256"
    stat_path.mkdir(parents=True, exist_ok=True)

    if df.empty:
        print("Warning: No data to chart. Skipping.")
        return

    has_resolution = "Resolution" in df.columns
    group_cols = ["Image Name", "Resolution"] if has_resolution else ["Image Name"]

    # df is already aggregated + ranked by main(); use it directly
    ranked_df = df

    unique_targets = ranked_df[group_cols].drop_duplicates()

    print("Generating tradeoff charts...")

    for _, target in unique_targets.iterrows():
        image_name = target["Image Name"]

        # Build the mask for this exact (image, resolution) slice
        mask = ranked_df["Image Name"] == image_name
        if has_resolution:
            resolution = target["Resolution"]
            mask &= ranked_df["Resolution"] == resolution

        image_df = ranked_df[mask].copy()

        if image_df.empty:
            continue

        # Pareto frontier computed once, for this single slice only
        frontier_df = pareto_frontier(image_df)

        best_row = image_df[image_df["Rank"] == 1].iloc[0]

        chart_title_suffix = f""
        safe_name_suffix = f"_{resolution}" if has_resolution else ""

        plt.style.use("seaborn-v0_8-whitegrid")
        fig, ax = plt.subplots(1, 1, figsize=(12, 8))

        unique_algs = image_df["Algorithm"].unique()
        color_palette = cm.get_cmap("tab20")(np.linspace(0, 1, len(unique_algs)))
        color_map = dict(zip(unique_algs, color_palette))
        point_colors = [color_map[alg] for alg in image_df["Algorithm"]]

        ax.scatter(
            image_df["Time Taken (ms)"],
            image_df["SSIM"],
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
                zorder=2,
                label="Pareto Frontier",
            )

        ax.scatter(
            best_row["Time Taken (ms)"],
            best_row["SSIM"],
            s=450,
            marker="*",
            facecolors="none",
            edgecolor="black",
            linewidth=1.5,
            zorder=4,
            label=f"Best Overall ({best_row['Algorithm']})",
        )

        texts = []
        for _, row in image_df.iterrows():
            is_best = row["Rank"] == 1
            texts.append(
                ax.text(
                    row["Time Taken (ms)"],
                    row["SSIM"],
                    row["Algorithm"],
                    fontsize=10 if not is_best else 12,
                    fontweight="bold" if is_best else "normal",
                    color="#1f2937",
                    zorder=5,
                )
            )

        adjust_text(texts, expand_points=(1.8, 1.8))

        ax.set_xscale("log")
        ax.set_xlabel("Avg Time Taken (ms)", fontsize=12, fontweight="medium")
        ax.set_ylabel("Avg SSIM", fontsize=12, fontweight="medium")
        ax.grid(True, which="major", axis="both", linestyle="-", alpha=0.4)
        ax.grid(True, which="minor", axis="x", linestyle=":", alpha=0.2)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        display_name = format_image_name(str(image_name))
        fig.suptitle(
            f"Algorithm Tradeoff (256 Colors): {display_name}{chart_title_suffix}",
            fontsize=16,
            fontweight="bold",
            y=0.96,
        )

        legend = ax.legend(loc="lower right", frameon=True, fontsize=10)
        legend.get_frame().set_alpha(0.9)
        legend.get_frame().set_edgecolor("#e5e7eb")

        fig.tight_layout()

        safe_name = Path(str(image_name)).stem
        output_file = stat_path / f"{safe_name}{safe_name_suffix}_tradeoff_chart_256.png"
        plt.savefig(output_file, bbox_inches="tight", dpi=300, facecolor="white")
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

    required_columns = {"Image Name", "Algorithm", "Time Taken (ms)", "SSIM", "Target Colors"}
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(f"CSV file '{csv_path}' is missing: {', '.join(sorted(missing_columns))}")

    df = df[df["Algorithm"] != "Shader-Acerola"].copy()

    df["Target Colors"] = pd.to_numeric(df["Target Colors"], errors="coerce")
    df = df[df["Target Colors"] == 256].copy()

    if df.empty:
        print("No data found for Target Colors = 256. Exiting.")
        return

    has_resolution = "Resolution" in df.columns
    group_cols = ["Image Name", "Resolution"] if has_resolution else ["Image Name"]

    print("Aggregating data by Algorithm for 256 colors...")
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

    output_csv_path = charts_dir / "ranked_benchmarks_256.csv"
    charts_dir.mkdir(parents=True, exist_ok=True)
    ranked_df.to_csv(output_csv_path, index=False)
    print(f"Saved ranked data to: {output_csv_path}")

    generate_tradeoff_charts(ranked_df, charts_dir)
    print("--- Tradeoff analysis completed successfully ---")


if __name__ == "__main__":
    main()
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.macros import OUTPUT_STATS_DIR


VALID_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".tiff", ".bmp")
DEFAULT_SINGLE_IMAGE_ROOT = PROJECT_ROOT / "assets" / "input" / "raw_images" / "single_image"


def load_rgb_image(image_path: Path) -> np.ndarray:
    image_bgr = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image_bgr is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")
    return cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)


def format_image_name(image_name: str) -> str:
    if image_name.lower().startswith("woods_"):
        suffix = image_name.split("_", 1)[1]
        return f"Woods {suffix}"
    return image_name.replace("_", " ").title()


def generate_speed_charts(df: pd.DataFrame, output_dir: Path) -> None:
    stat_path = output_dir / "image_charts"
    stat_path.mkdir(parents=True, exist_ok=True)

    df = df[df["Algorithm"] != "Shader-Acerola"].copy()
    unique_images = df["Image Name"].dropna().unique()
    print(f"Found {len(unique_images)} unique images. Generating speed charts...")

    for image_name in unique_images:
        image_df = df[df["Image Name"] == image_name].copy()
        image_df = image_df.dropna(subset=["Time Taken (ms)"])

        if image_df.empty:
            continue

        avg_df = image_df.groupby(["Target Colors", "Algorithm"])["Time Taken (ms)"].mean().reset_index()
        target_order = sorted(avg_df["Target Colors"].dropna().unique().tolist())
        algorithm_order = (
            avg_df.groupby("Algorithm")["Time Taken (ms)"].mean().sort_values(ascending=True).index.tolist()
        )

        algorithm_colors = {
            algorithm: plt.cm.tab10(index % 10)
            for index, algorithm in enumerate(algorithm_order)
        }

        plt.style.use("seaborn-v0_8-whitegrid")
        fig, ax = plt.subplots(1, 1, figsize=(14, 7))

        group_width = 0.8
        x_positions = np.arange(len(target_order)) * 1.6
        max_bars = max(
            avg_df[avg_df["Target Colors"] == target_color]["Algorithm"].nunique()
            for target_color in target_order
        )
        bar_width = group_width / max(1, max_bars)

        for x_position, target_color in zip(x_positions, target_order):
            color_df = avg_df[avg_df["Target Colors"] == target_color].copy()
            color_df = color_df.sort_values("Time Taken (ms)", ascending=True)

            values = color_df["Time Taken (ms)"].tolist()
            algorithms = color_df["Algorithm"].tolist()
            total_width = bar_width * len(values)
            start = x_position - total_width / 2 + bar_width / 2

            for bar_index, (algorithm, time_value) in enumerate(zip(algorithms, values)):
                left = start + bar_index * bar_width
                ax.bar(
                    left,
                    time_value,
                    width=bar_width,
                    color=algorithm_colors[algorithm],
                    align="center",
                    edgecolor="none",
                )

        ax.set_xticks(x_positions)
        ax.set_xticklabels(target_order, rotation=0)
        ax.set_title("Avg. Time Taken (ms)", pad=15)
        ax.set_xlabel("")
        ax.set_ylabel("ms (log scale)")
        ax.set_yscale("log")
        ax.grid(axis="y", linestyle="--", alpha=0.7)
        ax.grid(axis="x", visible=False)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        display_name = format_image_name(str(image_name))
        fig.suptitle(display_name, fontsize=16, fontweight="bold", y=1.02)

        legend_order = [algorithm for algorithm in algorithm_order if algorithm in algorithm_colors]
        ordered_handles = [Patch(facecolor=algorithm_colors[algorithm], label=algorithm) for algorithm in legend_order]
        fig.legend(
            ordered_handles,
            legend_order,
            loc="lower center",
            ncol=len(legend_order),
            bbox_to_anchor=(0.5, -0.0),
            frameon=False,
            handletextpad=0.5,
        )

        fig.subplots_adjust(top=0.88)

        safe_name = Path(str(image_name)).stem
        output_file = stat_path / f"{safe_name}_speed_chart.png"
        plt.savefig(output_file, bbox_inches="tight", dpi=300)
        plt.close()

        print(f"Generated: {output_file.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate speed charts from a benchmark CSV")
    parser.add_argument("csv", type=str, help="Path to the benchmark CSV file")
    parser.add_argument(
        "--charts-dir",
        type=str,
        default=str(OUTPUT_STATS_DIR),
        help="Directory where the speed charts will be written",
    )

    args = parser.parse_args()

    csv_path = Path(args.csv)
    charts_dir = Path(args.charts_dir)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    df = pd.read_csv(csv_path)

    if "Time Taken (ms)" not in df.columns:
        raise ValueError(f"CSV file '{csv_path}' does not contain a 'Time Taken (ms)' column.")

    generate_speed_charts(df, charts_dir)
    print("--- Speed analysis completed successfully ---")


if __name__ == "__main__":
    main()
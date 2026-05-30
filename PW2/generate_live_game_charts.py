import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.macros import OUTPUT_STATS_DIR

DEFAULT_CSV_PATH = OUTPUT_STATS_DIR / "camera_fps" / "live_camera_fps_1.csv"

def generate_live_fps_charts(csv_path: Path):
    if not csv_path.exists():
        print(f"Error: CSV file '{csv_path}' not found. Please run the benchmark first.")
        return

    df = pd.read_csv(csv_path)

    # Required columns
    required_cols = {'Resolution', 'Algorithm', 'Colors', 'Avg FPS', 'Avg Full Loop (ms)', 'Avg C++ Math (ms)'}
    missing = required_cols - set(df.columns)
    if missing:
        print(f"Error: Missing columns in CSV: {missing}")
        return

    out_dir = csv_path.parent / "live_game_charts"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Ignore Shader-Acerola
    df = df[df["Algorithm"] != "Shader-Acerola"].copy()

    unique_resolutions = df["Resolution"].unique()
    print(f"Found {len(unique_resolutions)} unique resolutions. Generating charts...")

    for resolution in unique_resolutions:
        res_df = df[df["Resolution"] == resolution].copy()

        target_order = sorted(res_df["Colors"].dropna().unique().tolist())
        algorithm_order = res_df.groupby("Algorithm")["Avg FPS"].mean().sort_values(ascending=False).index.tolist()
        
        algorithm_colors = {
            algorithm: plt.cm.tab10(index % 10)
            for index, algorithm in enumerate(algorithm_order)
        }

        # Create plot for Avg FPS
        plt.style.use("seaborn-v0_8-whitegrid")
        fig, ax_fps = plt.subplots(1, 1, figsize=(14, 7))

        group_width = 0.8
        x_positions = np.arange(len(target_order)) * 1.6
        max_bars = len(algorithm_order)
        bar_width = group_width / max(1, max_bars)

        for x_position, target_color in zip(x_positions, target_order):
            c_df = res_df[res_df["Colors"] == target_color].copy()

            # Align bars consistently by algorithm_order
            total_width = bar_width * len(algorithm_order)
            start = x_position - total_width / 2 + bar_width / 2

            for bar_index, algorithm in enumerate(algorithm_order):
                row = c_df[c_df["Algorithm"] == algorithm]
                if not row.empty:
                    val_fps = row["Avg FPS"].values[0]
                    left = start + bar_index * bar_width

                    ax_fps.bar(left, val_fps, width=bar_width, color=algorithm_colors[algorithm], edgecolor="none")

        # Format FPS Chart
        ax_fps.set_xticks(x_positions)
        ax_fps.set_xticklabels(target_order, rotation=0)
        ax_fps.set_title("Avg FPS", pad=15)
        ax_fps.set_xlabel("Target Colors")
        ax_fps.set_ylabel("FPS")
        ax_fps.grid(axis="y", linestyle="--", alpha=0.7)
        ax_fps.grid(axis="x", visible=False)
        ax_fps.spines["top"].set_visible(False)
        ax_fps.spines["right"].set_visible(False)
        
        # Add 60 FPS reference line
        ax_fps.axhline(60, color='red', linestyle=':', alpha=0.5)

        fig.suptitle(f"Live Game Capture Benchmark ({resolution})", fontsize=16, fontweight="bold", y=1.05)

        legend_order = algorithm_order
        ordered_handles = [Patch(facecolor=algorithm_colors[algorithm], label=algorithm) for algorithm in legend_order]
        
        fig.legend(
            ordered_handles,
            legend_order,
            loc="lower center",
            ncol=len(ordered_handles),
            bbox_to_anchor=(0.5, -0.05),
            frameon=False,
            handletextpad=0.5,
        )

        plt.tight_layout()

        safe_res = resolution.replace(" ", "")
        output_file = out_dir / f"live_game_comparison_{safe_res}.png"
        plt.savefig(output_file, bbox_inches="tight", dpi=300)
        plt.close()
        print(f"Generated chart: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Generate live game FPS charts from benchmark CSV.")
    parser.add_argument(
        "--csv",
        type=str,
        default=str(DEFAULT_CSV_PATH),
        help="Path to the live game FPS benchmark CSV file.",
    )
    args = parser.parse_args()

    generate_live_fps_charts(Path(args.csv))


if __name__ == "__main__":
    main()
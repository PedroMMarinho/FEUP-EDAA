from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from skimage.metrics import structural_similarity as skimage_ssim
from matplotlib.patches import Patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.macros import OUTPUT_STATS_DIR


VALID_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".tiff", ".bmp")
DEFAULT_SINGLE_IMAGE_ROOT = PROJECT_ROOT / "assets" / "input" / "raw_images" / "single_image"


def resolve_original_image(image_name: str, search_root: Path) -> Path | None:
    for extension in VALID_IMAGE_EXTENSIONS:
        candidate = search_root / f"{image_name}{extension}"
        if candidate.exists():
            return candidate

    return None


def resolve_processed_image(image_name: str, algorithm: str, target_colors: int, images_root: Path) -> Path:
    return images_root / algorithm / f"color_{target_colors}" / f"{image_name}.png"


def load_rgb_image(image_path: Path) -> np.ndarray:
    image_bgr = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image_bgr is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")
    return cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)


def calculate_ssim(original: np.ndarray, processed: np.ndarray) -> float:
    if original.shape[:2] != processed.shape[:2]:
        processed = cv2.resize(processed, (original.shape[1], original.shape[0]), interpolation=cv2.INTER_AREA)

    return float(
        skimage_ssim(
            original,
            processed,
            channel_axis=2,
            data_range=255,
        )
    )


def format_image_name(image_name: str) -> str:
    if image_name.lower().startswith("woods_"):
        suffix = image_name.split("_", 1)[1]
        return f"Woods {suffix}"

    return image_name.replace("_", " ").title()


def generate_ssim_charts(df: pd.DataFrame, output_dir: Path) -> None:
    stat_path = output_dir / "image_charts"
    stat_path.mkdir(parents=True, exist_ok=True)

    df = df[df["Algorithm"] != "Shader-Acerola"].copy()
    unique_images = df["Image Name"].dropna().unique()
    print(f"Found {len(unique_images)} unique images. Generating SSIM charts...")

    for image_name in unique_images:
        image_df = df[df["Image Name"] == image_name].copy()
        image_df = image_df.dropna(subset=["SSIM"])

        if image_df.empty:
            continue

        avg_df = image_df.groupby(["Target Colors", "Algorithm"])["SSIM"].mean().reset_index()
        target_order = sorted(avg_df["Target Colors"].dropna().unique().tolist())
        algorithm_order = avg_df.groupby("Algorithm")["SSIM"].mean().sort_values(ascending=False).index.tolist()

        algorithm_colors = {
            algorithm: plt.cm.tab10(index % 10)
            for index, algorithm in enumerate(algorithm_order)
        }

        plt.style.use("seaborn-v0_8-whitegrid")
        fig, ax = plt.subplots(1, 1, figsize=(14, 7))

        group_width = 0.8
        max_bars = max(
            avg_df[avg_df["Target Colors"] == target_color]["Algorithm"].nunique()
            for target_color in target_order
        )
        bar_width = group_width / max(1, max_bars)

        for x_index, target_color in enumerate(target_order):
            color_df = avg_df[avg_df["Target Colors"] == target_color].copy()
            color_df = color_df.sort_values("SSIM", ascending=False)

            values = color_df["SSIM"].tolist()
            algorithms = color_df["Algorithm"].tolist()
            total_width = bar_width * len(values)
            start = x_index - total_width / 2 + bar_width / 2

            for bar_index, (algorithm, ssim_value) in enumerate(zip(algorithms, values)):
                left = start + bar_index * bar_width
                ax.bar(
                    left,
                    ssim_value,
                    width=bar_width,
                    color=algorithm_colors[algorithm],
                    align="center",
                    edgecolor="none",
                )

        ax.set_xticks(range(len(target_order)))
        ax.set_xticklabels(target_order, rotation=0)
        ax.set_title("Avg. SSIM", pad=15)
        ax.set_xlabel("")
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
            ncol=min(len(legend_order),
            bbox_to_anchor=(0.5, -0.05),
            frameon=False,
            handletextpad=0.5,
        )

        plt.tight_layout()

        safe_name = Path(str(image_name)).stem
        output_file = stat_path / f"{safe_name}_ssim_chart.png"
        plt.savefig(output_file, bbox_inches="tight", dpi=300)
        plt.close()

        print(f"Generated: {output_file.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate SSIM charts from an SSIM-enriched benchmark CSV")
    parser.add_argument("csv", type=str, help="Path to the benchmark CSV file")
    parser.add_argument(
        "--charts-dir",
        type=str,
        default=str(OUTPUT_STATS_DIR),
        help="Directory where the SSIM charts will be written",
    )

    args = parser.parse_args()

    csv_path = Path(args.csv)
    charts_dir = Path(args.charts_dir)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    enriched_df = pd.read_csv(csv_path)

    if "SSIM" not in enriched_df.columns:
        raise ValueError(f"CSV file '{csv_path}' does not contain an SSIM column.")

    generate_ssim_charts(enriched_df, charts_dir)
    print("--- SSIM analysis completed successfully ---")


if __name__ == "__main__":
    main()

from pathlib import Path


CSV_FILE = Path("assets/output/csv/benchmark_stats.csv")
OUTPUT_CSV_DIR = Path("assets/output/csv")
OUTPUT_IMAGE_DIR = Path("assets/output/modified_images")
LIB_PATH = Path("core/cpp/octree_lib.so").resolve()
ALGORITHMS = [
    "Octree-Baseline",
    "Octree-Two-Pass",
    "Median-Cut",
    "K-Means",
    "Uniform"
]

from pathlib import Path


CSV_FILE = Path("assets/output/csv/benchmark_stats.csv")
OUTPUT_DIR = Path("assets/output/modified_images")
ALGORITHMS = [
    "Octree-Baseline",
    "Greedy",
    "Median-Cut",
    "K-Means",
    "Uniform"
]
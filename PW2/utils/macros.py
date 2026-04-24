
import ctypes
from pathlib import Path

OUTPUT_STATS_DIR = Path("assets/output/statistics")
OUTPUT_CSV_DIR = Path("assets/output/csv")
OUTPUT_IMAGE_DIR = Path("assets/output/modified_images")
LIB_PATH = Path("core/cpp/octree_lib.so").resolve()
LIB = ctypes.CDLL(str(LIB_PATH))
ALGORITHMS = [
    "Octree-Baseline",
    "Median-Cut",
    "K-Means",
    "SOM",
    "Octree-SOM",
    "Octree-K-Means",
]
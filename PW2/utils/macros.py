
import ctypes
from pathlib import Path
import platform

OUTPUT_STATS_DIR = Path("assets/output/statistics")
OUTPUT_CSV_DIR = Path("assets/output/csv")
OUTPUT_IMAGE_DIR = Path("assets/output/modified_images")
OUTPUT_VIDEO_DIR = Path("assets/output/modified_videos")
PALLETES_DIR = Path("palletes")

if platform.system() == "Windows":
    LIB_PATH = Path("core/cpp/octree_lib.dll")
else:
    LIB_PATH = Path("core/cpp/octree_lib.so")

LIB = ctypes.CDLL(str(LIB_PATH.resolve()))
ALGORITHMS = [
    "Octree-Baseline",
    "Median-Cut",
    "K-Means",
    "SOM",
    "Octree-SOM",
    "Octree-K-Means",
    "Shader-Acerola"
]
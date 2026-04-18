import ctypes
from pathlib import Path

import numpy as np
from PIL import Image
from core.py.octree import Octree
from utils.macros import LIB_PATH


def run_algorithm(algo: str, original_image: Image.Image, target_colors: int) -> Image.Image:
    print(f"Running {algo} algorithm with target colors: {target_colors}")
    match algo:
        case "Octree-Baseline":
            return octree_baseline(original_image, target_colors)
        case "Greedy":
            return None
        case "Median-Cut":
            return None
        case "K-Means":
            return None
        case "Uniform":
            return None
        case _:
            raise ValueError(f"Unknown algorithm: {algo}")

# --- 1. Octree Baseline Implementation 
lib = ctypes.CDLL(str(LIB_PATH))
lib.octree_quantize_baseline.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_int, ctypes.c_int]

def octree_baseline(original_image: Image.Image, target_colors: int) -> Image.Image:
    
    pixels = np.ascontiguousarray(np.array(original_image, dtype=np.uint8))
    
    total_pixels = pixels.shape[0] * pixels.shape[1]
    
    pixel_ptr = pixels.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
    
    lib.octree_quantize_baseline(pixel_ptr, total_pixels, target_colors)
    
    return Image.fromarray(pixels, 'RGB')
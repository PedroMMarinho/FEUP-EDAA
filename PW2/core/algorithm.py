import ctypes
from pathlib import Path

import numpy as np
from PIL import Image
from utils.macros import LIB


def run_algorithm(algo: str, original_image_frame: np.ndarray, target_colors: int) -> np.ndarray:
    #print(f"Running {algo} algorithm with target colors: {target_colors}")
    match algo:
        case "Octree-Baseline":
            return octree_baseline(original_image_frame, target_colors)
        case "Median-Cut":
            return median_cut(original_image_frame, target_colors)
        case "K-Means":
            return kmeans(original_image_frame, target_colors)
        case "SOM":
            return som(original_image_frame, target_colors)
        case "Octree-SOM":
            return som_octree(original_image_frame, target_colors)
        case "Octree-K-Means":
            return None  # Placeholder for future implementation
        case "Octree-Live":
            return octree_quantize_live(original_image_frame, target_colors)
        case _:
            raise ValueError(f"Unknown algorithm: {algo}")

LIB.octree_quantize_live.restype  = None
LIB.octree_quantize_live.argtypes = [
    ctypes.POINTER(ctypes.c_uint8),
    ctypes.c_int,  
    ctypes.c_int, 
]

# Not that much of a difference but will use it in game loop 
def octree_quantize_live(original_image_frame: np.ndarray, target_colors: int) -> Image.Image:
    n = original_image_frame.shape[0] * original_image_frame.shape[1]
    ptr = original_image_frame.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
    LIB.octree_quantize_live(ptr, n, target_colors)
    return original_image_frame    

LIB.octree_quantize_baseline.restype  = None
LIB.octree_quantize_baseline.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_int, ctypes.c_int]

def octree_baseline(original_image_frame: np.ndarray, target_colors: int) -> Image.Image:
    total_original_image_frame = original_image_frame.shape[0] * original_image_frame.shape[1]
    pixel_ptr = original_image_frame.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
    
    LIB.octree_quantize_baseline(pixel_ptr, total_original_image_frame, target_colors)
    
    return original_image_frame

def median_cut(original_image_frame: np.ndarray, target_colors: int) -> Image.Image:

    quantized_array = (original_image_frame >> 3) << 3
    
    temp_image = Image.fromarray(quantized_array, 'RGB')
    

    res = temp_image.quantize(
        colors=target_colors, 
        method=Image.Quantize.MEDIANCUT, 
        dither=Image.Dither.NONE
    ).convert('RGB')

    return np.array(res, dtype=np.uint8)


LIB.kmeans_quantize.restype  = None
LIB.kmeans_quantize.argtypes = [
    ctypes.POINTER(ctypes.c_uint8),   
    ctypes.c_int,                      
    ctypes.c_int,                      
    ctypes.c_int,                      
    ctypes.c_int,                      
    ctypes.c_uint32,                  
]
def kmeans(original_image_frame: np.ndarray, target_colors: int,
           max_iter: int = 20, seed: int = 42) -> Image.Image:
    h, w = original_image_frame.shape[:2]
    ptr = original_image_frame.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
    LIB.kmeans_quantize(ptr, w, h, target_colors, max_iter, seed)
    return original_image_frame

LIB.som_quantize.restype  = None
LIB.som_quantize.argtypes = [
    ctypes.POINTER(ctypes.c_uint8), 
    ctypes.c_int,                     
    ctypes.c_int,                     
    ctypes.c_int,                    
    ctypes.c_int,                     
    ctypes.c_float,                   
    ctypes.c_float,                   
    ctypes.c_float,                   
    ctypes.c_uint32,                  
]

def som(original_image_frame: np.ndarray, target_colors: int) -> Image.Image:
    h, w = original_image_frame.shape[:2]
    n = h * w
    ptr = original_image_frame.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
    LIB.som_quantize(ptr, w, h,
                     target_colors,
                     n * 2,              
                     0.62,                
                     float(target_colors) / 2.0, 
                     1e-4,               
                     42)                 
    return original_image_frame



LIB.som_octree_quantize.restype  = None
LIB.som_octree_quantize.argtypes = [
    ctypes.POINTER(ctypes.c_uint8),  # original_image_frame
    ctypes.c_int,                     # width
    ctypes.c_int,                     # height
    ctypes.c_int,                     # K
    ctypes.c_float,                   # alpha_winner
    ctypes.c_float,                   # threshold
    ctypes.c_int,                     # subset_size (0 = all original_image_frame)
    ctypes.c_uint32,                  # seed
]

def som_octree(original_image_frame: np.ndarray, target_colors: int) -> Image.Image:
    h, w = original_image_frame.shape[:2]
    ptr = original_image_frame.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
    LIB.som_octree_quantize(ptr, w, h,
                            target_colors,
                            0.5,      # alpha_winner
                            0.025,    # threshold — paper's recommended value
                            5000,     # subset_size per iteration
                            42)
    return original_image_frame
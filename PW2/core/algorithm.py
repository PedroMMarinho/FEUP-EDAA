import ctypes
from pathlib import Path

import numpy as np
from PIL import Image
from utils.macros import LIB

LIB.octree_quantize_baseline.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_int, ctypes.c_int]

def run_algorithm(algo: str, original_image: Image.Image, target_colors: int) -> Image.Image:
    print(f"Running {algo} algorithm with target colors: {target_colors}")
    match algo:
        case "Octree-Baseline":
            return octree_baseline(original_image, target_colors)
        case "Median-Cut":
            return median_cut(original_image, target_colors)
        case "K-Means":
            return kmeans(original_image, target_colors)
        case "SOM":
            return som(original_image, target_colors)
        case "Octree-SOM":
            return som_octree(original_image, target_colors)
        case "Octree-K-Means":
            return None  # Placeholder for future implementation
        case _:
            raise ValueError(f"Unknown algorithm: {algo}")


def octree_baseline(original_image: Image.Image, target_colors: int) -> Image.Image:
    pixels = np.ascontiguousarray(np.array(original_image, dtype=np.uint8))
    total_pixels = pixels.shape[0] * pixels.shape[1]
    pixel_ptr = pixels.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
    
    LIB.octree_quantize_baseline(pixel_ptr, total_pixels, target_colors)
    
    return Image.fromarray(pixels, 'RGB')

def median_cut(original_image: Image.Image, target_colors: int) -> Image.Image:

    img_array = np.array(original_image, dtype=np.uint8)

    quantized_array = (img_array >> 3) << 3
    
    temp_image = Image.fromarray(quantized_array, 'RGB')
    

    return temp_image.quantize(
        colors=target_colors, 
        method=Image.Quantize.MEDIANCUT, 
        dither=Image.Dither.NONE
    ).convert('RGB')


LIB.kmeans_quantize.restype  = None
LIB.kmeans_quantize.argtypes = [
    ctypes.POINTER(ctypes.c_uint8),   
    ctypes.c_int,                      
    ctypes.c_int,                      
    ctypes.c_int,                      
    ctypes.c_int,                      
    ctypes.c_uint32,                  
]
def kmeans(original_image: Image.Image, target_colors: int,
           max_iter: int = 20, seed: int = 42) -> Image.Image:
    pixels = np.ascontiguousarray(np.array(original_image, dtype=np.uint8))
    h, w = pixels.shape[:2]
    ptr = pixels.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
    LIB.kmeans_quantize(ptr, w, h, target_colors, max_iter, seed)
    return Image.fromarray(pixels, 'RGB')

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

def som(original_image: Image.Image, target_colors: int) -> Image.Image:
    pixels = np.ascontiguousarray(np.array(original_image, dtype=np.uint8))
    h, w = pixels.shape[:2]
    n = h * w
    ptr = pixels.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
    LIB.som_quantize(ptr, w, h,
                     target_colors,
                     n * 2,              
                     0.62,                
                     float(target_colors) / 2.0, 
                     1e-4,               
                     42)                 
    return Image.fromarray(pixels, 'RGB')


LIB.som_octree_quantize.restype  = None
LIB.som_octree_quantize.argtypes = [
    ctypes.POINTER(ctypes.c_uint8),  
    ctypes.c_int,                     
    ctypes.c_int,                     
    ctypes.c_int,                     
    ctypes.c_int,                    
    ctypes.c_int,                     
    ctypes.c_float,                   
    ctypes.c_float,                   
    ctypes.c_float,                  
    ctypes.c_uint32,                 
]

def som_octree(original_image: Image.Image, target_colors: int) -> Image.Image:
    pixels = np.ascontiguousarray(np.array(original_image, dtype=np.uint8))
    h, w = pixels.shape[:2]
    n = h * w
    ptr = pixels.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
    intermediate = min(n, 4096)
    LIB.som_octree_quantize(ptr, w, h,
                            target_colors,
                            intermediate,
                            intermediate * 2,    
                            0.62,
                            float(target_colors) / 2.0,
                            1e-4,
                            42)
    return Image.fromarray(pixels, 'RGB')
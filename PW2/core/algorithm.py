import ctypes
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from utils.macros import LIB
from utils.pallete import get_palette

def run_algorithm(algo: str, original_image_frame: np.ndarray, target_colors: int) -> np.ndarray:
    if not original_image_frame.flags['C_CONTIGUOUS']:
        original_image_frame = np.ascontiguousarray(original_image_frame)

    match algo:
        case "Octree-Euclidean":
            return octree_euclidean(original_image_frame, target_colors)
        case "Median-Cut":
            return median_cut(original_image_frame, target_colors)
        case "Uniform":
            return uniform_quantize(original_image_frame, target_colors)
        case "K-Means":
            return kmeans(original_image_frame, target_colors)
        case "SOM":
            return som(original_image_frame, target_colors)
        case "Octree-SOM":
            return som_octree(original_image_frame, target_colors)
        case "Octree-K-Means":
            return octree_kmeans(original_image_frame, target_colors)
        case "Octree-Live":
            return octree_quantize_live(original_image_frame, target_colors)
        case "Octree-Baseline":
            return octree_baseline(original_image_frame, target_colors)
        case "Shader-Acerola":
            return shader_acerola(original_image_frame, target_colors)
        case _:
            raise ValueError(f"Unknown algorithm: {algo}")

LIB.acerola_dither_uniform.restype = None
LIB.acerola_dither_uniform.argtypes = [
    ctypes.POINTER(ctypes.c_uint8), # pixels
    ctypes.c_int,                   # width
    ctypes.c_int,                   # height
    ctypes.c_int,                   # steps_per_channel
    ctypes.c_float                  # spread
]

LIB.acerola_dither_palette.restype = None
LIB.acerola_dither_palette.argtypes = [
    ctypes.POINTER(ctypes.c_uint8), # pixels
    ctypes.c_int,                   # width
    ctypes.c_int,                   # height
    ctypes.POINTER(ctypes.c_uint8), # palette array
    ctypes.c_int,                   # palette_size
    ctypes.c_float                  # spread
]

LIB.extract_octree_palette.restype = ctypes.c_int
LIB.extract_octree_palette.argtypes = [
    ctypes.POINTER(ctypes.c_uint8), # pixels
    ctypes.c_int,                   # width
    ctypes.c_int,                   # height
    ctypes.c_int,                   # maxColors
    ctypes.POINTER(ctypes.c_uint8)  # out_palette (pre-allocated buffer)
]

LIB.uniform_quantize.restype = None
LIB.uniform_quantize.argtypes = [
    ctypes.POINTER(ctypes.c_uint8), # pixels
    ctypes.c_int,                   # width
    ctypes.c_int,                   # height
    ctypes.c_int,                   # target_colors
]


def shader_acerola(original_image_frame: np.ndarray, 
                   target_colors: int) -> np.ndarray:
    h, w = original_image_frame.shape[:2]
    
    # ---------------------------------------------------------
    # TWEAKABLE FIELDS
    pixel_scale = 1             # 1 = HD, 4 = GBA style, 8 = Gameboy style
    apply_sharpness = False     # True = Acerola's edge enhancing matrix
    custom_spread = 0           # None = Auto-calculate mathematically perfect spread
    use_palette = False         # True = Extract custom palette from image, False = Uniform quantization
    pallete_file = "slso8"      # Name of the custom palette to use
    use_octree_pallete = False
    # ---------------------------------------------------------

    # ==========================================
    # STEP 1: PRE-PROCESSING (Downscale & Sharpen)
    # ==========================================
    if pixel_scale > 1:
        down_w, down_h = w // pixel_scale, h // pixel_scale
        working_frame = cv2.resize(original_image_frame, (down_w, down_h), interpolation=cv2.INTER_NEAREST)
    else:
        working_frame = original_image_frame.copy() 
        down_w, down_h = w, h

    if apply_sharpness:
        kernel = np.array([[ 0, -1,  0], [-1,  5, -1], [ 0, -1,  0]])
        working_frame = cv2.filter2D(working_frame, -1, kernel)

    if not working_frame.flags['C_CONTIGUOUS']:
        working_frame = np.ascontiguousarray(working_frame)

    work_pixel_ptr = working_frame.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))

    # ==========================================
    # STEP 2: DITHERING LOGIC BRANCH
    # ==========================================
    
    if use_palette:

        if use_octree_pallete:
            # --- PATH A: OCTREE PALETTE DITHERING ---
            if not original_image_frame.flags['C_CONTIGUOUS']:
                original_image_frame = np.ascontiguousarray(original_image_frame)
            orig_pixel_ptr = original_image_frame.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
            # 1. Extract Palette
            raw_palette_buffer = np.zeros((target_colors, 3), dtype=np.uint8)
            palette_ptr = raw_palette_buffer.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
            actual_colors = LIB.extract_octree_palette(orig_pixel_ptr, w, h, target_colors, palette_ptr)
            # 2. Sort Palette by Luminance
            unsorted_palette = raw_palette_buffer[:actual_colors]
            luminance = (0.299 * unsorted_palette[:, 0] + 
                         0.587 * unsorted_palette[:, 1] + 
                         0.114 * unsorted_palette[:, 2])
            sorted_indices = np.argsort(luminance)
            custom_palette = unsorted_palette[sorted_indices]
        else:
            # Apply hardcoded pallet
            custom_palette = get_palette(pallete_file)
            actual_colors = len(custom_palette)

        flat_palette = custom_palette.flatten()
        flat_pal_ptr = flat_palette.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
        spread = custom_spread if custom_spread is not None else (1.0 / (actual_colors - 1.0))
        
        LIB.acerola_dither_palette(work_pixel_ptr, down_w, down_h, flat_pal_ptr, actual_colors, spread)

    else:
        steps_per_channel = max(2, int(round(target_colors ** (1/3.0))))
        spread = custom_spread if custom_spread is not None else (1.0 / (steps_per_channel - 1.0))
        
        LIB.acerola_dither_uniform(work_pixel_ptr, down_w, down_h, steps_per_channel, spread)


    # ==========================================
    # STEP 3: POST-PROCESSING (Upscale)
    # ==========================================
    if pixel_scale > 1:
        final_frame = cv2.resize(working_frame, (w, h), interpolation=cv2.INTER_NEAREST)
    else:
        final_frame = working_frame

    return final_frame





LIB.octree_quantize_live.restype  = None
LIB.octree_quantize_live.argtypes = [
    ctypes.POINTER(ctypes.c_uint8),
    ctypes.c_int,  
    ctypes.c_int, 
]

def octree_quantize_live(original_image_frame: np.ndarray, target_colors: int) -> np.ndarray:
    n = original_image_frame.shape[0] * original_image_frame.shape[1]
    ptr = original_image_frame.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
    LIB.octree_quantize_live(ptr, n, target_colors)
    return original_image_frame    

LIB.octree_quantize_euclidean.restype  = None
LIB.octree_quantize_euclidean.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_int, ctypes.c_int]

def octree_euclidean(original_image_frame: np.ndarray, target_colors: int) -> np.ndarray:
    total_original_image_frame = original_image_frame.shape[0] * original_image_frame.shape[1]
    pixel_ptr = original_image_frame.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
    LIB.octree_quantize_euclidean(pixel_ptr, total_original_image_frame, target_colors)
    return original_image_frame

LIB.octree_quantize_baseline.restype  = None
LIB.octree_quantize_baseline.argtypes = [
    ctypes.POINTER(ctypes.c_uint8),   # original_image_frame
    ctypes.c_int,                     # total_original_image_frame
    ctypes.c_int,                     # target_colors
]

def octree_baseline(original_image_frame: np.ndarray, target_colors: int) -> np.ndarray:
    total_original_image_frame = original_image_frame.shape[0] * original_image_frame.shape[1]
    pixel_ptr = original_image_frame.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
    LIB.octree_quantize_baseline(pixel_ptr, total_original_image_frame, target_colors)
    return original_image_frame


def median_cut(original_image_frame: np.ndarray, target_colors: int) -> np.ndarray:
    quantized_array = (original_image_frame >> 3) << 3
    temp_image = Image.fromarray(quantized_array, 'RGB')
    
    res = temp_image.quantize(
        colors=target_colors, 
        method=Image.Quantize.MEDIANCUT, 
        dither=Image.Dither.NONE
    ).convert('RGB')

    return np.array(res, dtype=np.uint8)


def uniform_quantize(original_image_frame: np.ndarray, target_colors: int) -> np.ndarray:
    h, w = original_image_frame.shape[:2]
    ptr = original_image_frame.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
    LIB.uniform_quantize(ptr, w, h, target_colors)
    return original_image_frame

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
           max_iter: int = 20, seed: int = 42) -> np.ndarray:
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

def som(original_image_frame: np.ndarray, target_colors: int) -> np.ndarray:
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
    ctypes.POINTER(ctypes.c_uint8),   # original_image_frame
    ctypes.c_int,                     # width
    ctypes.c_int,                     # height
    ctypes.c_int,                     # K
    ctypes.c_float,                   # alpha_winner
    ctypes.c_float,                   # threshold
    ctypes.c_int,                     # subset_size (0 = all original_image_frame)
    ctypes.c_uint32,                  # seed
]

def som_octree(original_image_frame: np.ndarray, target_colors: int) -> np.ndarray:
    h, w = original_image_frame.shape[:2]
    ptr = original_image_frame.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
    LIB.som_octree_quantize(ptr, w, h,
                            target_colors,
                            0.5,      # alpha_winner
                            0.025,    # threshold — paper's recommended value
                            5000,     # subset_size per iteration
                            42)
    return original_image_frame

LIB.octree_kmeans_quantize.restype  = None
LIB.octree_kmeans_quantize.argtypes = [
    ctypes.POINTER(ctypes.c_uint8),   # pixels
    ctypes.c_int,                     # width
    ctypes.c_int,                     # height
    ctypes.c_int,                     # K
    ctypes.c_int,                     # max_iter
    ctypes.c_uint32,                  # seed
]

def octree_kmeans(original_image_frame: np.ndarray, target_colors: int) -> np.ndarray:
    h, w = original_image_frame.shape[:2]
    max_iter = 20
    seed = 42
    ptr = original_image_frame.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
    LIB.octree_kmeans_quantize(ptr, w, h, target_colors, max_iter, seed)
    return original_image_frame
import ctypes
import cv2
from PIL import Image
import csv
from utils.macros import LIB, LIB_PATH
import numpy as np

def load_image_data(filepath):
    img_bgr = cv2.imread(str(filepath))
    
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    
    return np.ascontiguousarray(img_rgb)

def save_image_output(image: np.ndarray, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(output_path), img_bgr)
    print(f"Saved output to: {output_path}")


def get_image_resolution(image_path):
    img = Image.open(image_path)
    return img.size

def get_image_color_count(image_path):
    img = Image.open(image_path).convert('RGB')
    colors = img.getcolors(maxcolors=10000000) 
    return len(colors) 

LIB.calculate_exact_color_difference.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_int]
LIB.calculate_exact_color_difference.restype = ctypes.c_double

def get_color_difference(image_path):
    img = Image.open(image_path).convert('RGB')
    
    pixels = np.ascontiguousarray(img).flatten()
    
    c_uint8_p = ctypes.POINTER(ctypes.c_uint8)
    pixel_ptr = pixels.ctypes.data_as(c_uint8_p)
    num_pixels = len(pixels) // 3
    
    result = LIB.calculate_exact_color_difference(pixel_ptr, num_pixels)
    return result

def calculate_error_metrics(original_img, processed_img):
    X = original_img.astype(np.float64)
    X_hat = processed_img.astype(np.float64)
    
    H, W = X.shape[:2]
    HW = H * W
    
    diff = X - X_hat
    
    mae = np.sum(np.abs(diff)) / HW
    mse = np.sum(diff ** 2) / HW
    
    return mae, mse


def load_hex_palette(filepath: str) -> np.ndarray:
    colors = []
    
    with open(filepath, 'r') as f:
        for line in f:
            hex_str = line.strip()
            if not hex_str: continue
            
            if hex_str.startswith('#'):
                hex_str = hex_str[1:]
            elif len(hex_str) == 8 and hex_str.upper().startswith('FF'):
                hex_str = hex_str[2:]
                
            r = int(hex_str[0:2], 16)
            g = int(hex_str[2:4], 16)
            b = int(hex_str[4:6], 16)
            colors.append([r, g, b])
            
    palette_array = np.array(colors, dtype=np.uint8)
    
    luminance = (0.299 * palette_array[:, 0] + 
                 0.587 * palette_array[:, 1] + 
                 0.114 * palette_array[:, 2])
    
    sorted_indices = np.argsort(luminance)
    return palette_array[sorted_indices]
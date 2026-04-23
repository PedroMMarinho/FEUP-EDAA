import ctypes

from PIL import Image
import csv
from utils.macros import CSV_FILE, LIB_PATH
import numpy as np

def load_image_data(filepath):
    return Image.open(filepath).convert('RGB')

def save_image_output(image, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    print(f"Saved output to: {output_path}")


def get_image_resolution(image_path):
    img = Image.open(image_path)
    return img.size

def get_image_color_count(image_path):
    img = Image.open(image_path).convert('RGB')
    colors = img.getcolors(maxcolors=10000000) 
    return len(colors) 

lib = ctypes.CDLL(str(LIB_PATH))
lib.calculate_exact_color_difference.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_int]
lib.calculate_exact_color_difference.restype = ctypes.c_double

def get_color_difference(image_path):
    img = Image.open(image_path).convert('RGB')
    
    pixels = np.ascontiguousarray(img).flatten()
    
    c_uint8_p = ctypes.POINTER(ctypes.c_uint8)
    pixel_ptr = pixels.ctypes.data_as(c_uint8_p)
    num_pixels = len(pixels) // 3
    
    result = lib.calculate_exact_color_difference(pixel_ptr, num_pixels)
    return result
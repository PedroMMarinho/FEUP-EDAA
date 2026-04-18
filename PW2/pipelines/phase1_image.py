from core.octree import Octree
from pathlib import Path
import numpy as np
from PIL import Image
from core.algorithm import run_algorithm
from utils.image_utils import load_image_data, save_output

def process_target(input_path_str: str, target_colors: int):
    input_path   = Path(input_path_str)
    output_base  = Path("assets/output/modified_images")
    valid_ext    = {'.png', '.jpg', '.jpeg', '.tiff', '.bmp'}

    if input_path.is_file():
        out_path = output_base
        run(input_path, out_path, target_colors)

    elif input_path.is_dir():
        print(f"Scanning directory: {input_path}")
        for file_path in input_path.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in valid_ext:
                relative  = file_path.relative_to(input_path)
                out_path  = output_base / relative.parent
                run(file_path, out_path, target_colors)
    else:
        print(f"Error: path '{input_path}' does not exist.")

# All algorithms that will be implemented 
algorithms = [
    "Octree-Baseline",  
    #"Greedy",      
    #"Median-Cut", 
    #"K-Means", 
    #"Uniform"          
]

def run(input_path: Path, output_base: Path, target_colors: int):
    clean_name = input_path.stem
    for algo in algorithms:
        processed_image = run_algorithm(algo, input_path, target_colors)
        final_output_path = output_base / algo / f"color_{target_colors}" / f"{clean_name}.png"
        save_output(processed_image, final_output_path)

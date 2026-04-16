from core.octree import Octree
from utils import save_output
from pathlib import Path
import numpy as np
from PIL import Image


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
algorithms = ["Greedy", "Random", "K-Means", "Median-Cut"]

def run(input_path: Path, output_base: Path, target_colors: int):
    clean_name = input_path.stem
    for algo in algorithms:
        processed_image = run_algorithm(algo, target_colors)
        output_base = output_base / algo / target_colors / f"{clean_name}.png"
        save_output(processed_image, input_path, output_base, algo)


def run_algorithm(algo: str, target_colors: int):
    print(f"Running {algo} algorithm with target colors: {target_colors}")
    match algo:
        case "Greedy":
            return greedy_algorithm(target_colors)
        case "Random":
            return random_algorithm(target_colors)
        case "K-Means":
            return kmeans_algorithm(target_colors)
        case "Median-Cut":
            return median_cut_algorithm(target_colors)
        case _:
            raise ValueError(f"Unknown algorithm: {algo}")
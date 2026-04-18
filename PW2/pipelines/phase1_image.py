import time

from pathlib import Path
from core.algorithm import run_algorithm
from utils.utils import get_image_color_count, get_image_resolution, load_image_data, save_output, save_to_csv
from utils.macros import ALGORITHMS, OUTPUT_DIR

def process_target(input_path_str: str, target_colors: int):
    input_path   = Path(input_path_str)
    output_base  = OUTPUT_DIR
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


def run(input_path: Path, output_base: Path, target_colors: int):
    clean_name = input_path.stem
    resolution = get_image_resolution(input_path)
    original_colors = get_image_color_count(input_path)

    original_image = load_image_data(input_path)
    for algo in ALGORITHMS:

        start_time = time.perf_counter()
        processed_image = run_algorithm(algo, original_image, target_colors)
        end_time = time.perf_counter()

        time_taken = end_time - start_time

        if processed_image is not None:
            final_output_path = output_base / algo / f"color_{target_colors}" / f"{clean_name}.png"
            save_output(processed_image, final_output_path)
            final_colors = get_image_color_count(final_output_path)
            save_to_csv(clean_name, resolution, algo, target_colors, original_colors, final_colors, time_taken)
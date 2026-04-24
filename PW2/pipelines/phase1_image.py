import time
from pathlib import Path
import pandas as pd
import re
import matplotlib.pyplot as plt
import numpy as np
from core.algorithm import run_algorithm
from utils.utils import calculate_error_metrics, get_color_difference, get_image_color_count, get_image_resolution, load_image_data, save_image_output
from utils.macros import ALGORITHMS, OUTPUT_CSV_DIR, OUTPUT_IMAGE_DIR, OUTPUT_STATS_DIR

def get_next_csv_path(output_dir: Path, base_name="benchmark_stats") -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    
    existing_files = list(output_dir.glob(f"{base_name}_*.csv"))
    
    if not existing_files:
        return output_dir / f"{base_name}_1.csv"
    
    max_num = 0
    for f in existing_files:
        try:
            num = int(f.stem.split('_')[-1])
            if num > max_num:
                max_num = num
        except ValueError:
            continue
            
    return output_dir / f"{base_name}_{max_num + 1}.csv"


def process_target(input_path_str: str, target_colors: int):
    input_path   = Path(input_path_str)
    output_base  = OUTPUT_IMAGE_DIR
    valid_ext    = {'.png', '.jpg', '.jpeg', '.tiff', '.bmp'}
    store_image_info = False

    current_run_csv = get_next_csv_path(OUTPUT_CSV_DIR)
    print(f"Results for this run will be saved to: {current_run_csv.name}")

    if input_path.is_file():
        out_path = output_base
        run(input_path, out_path, target_colors, current_run_csv)

    elif input_path.is_dir():
        print(f"Scanning directory: {input_path}")

        if store_image_info:
            test_image_info = pd.DataFrame(columns=[
                'Image Name', 'Resolution', 'Number of Colors', 'Color difference'
            ])
            rows = []

        for file_path in input_path.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in valid_ext:

                if store_image_info:
                    rows.append({
                                'Image Name': file_path.stem,
                                'Resolution': get_image_resolution(file_path),
                                'Number of Colors': get_image_color_count(file_path),
                                'Color difference': get_color_difference(file_path)
                            })
                    
                relative  = file_path.relative_to(input_path)
                out_path  = output_base / relative.parent
                
                run(file_path, out_path, target_colors, current_run_csv)

        if store_image_info:
            test_image_info = pd.DataFrame(rows)
            test_image_info.to_csv(OUTPUT_CSV_DIR / "test_image_info.csv", index=False)
    else:
        print(f"Error: path '{input_path}' does not exist.")


def run(input_path: Path, output_base: Path, target_colors: int, output_csv_path: Path):
    clean_name = input_path.stem
    resolution = get_image_resolution(input_path)
    original_colors = get_image_color_count(input_path)
    n_run_times = 10

    original_image = load_image_data(input_path)

    rows = []
    least_colors = 8

    for algo in ALGORITHMS:
       
        current_colors = least_colors
        while current_colors <= target_colors:
            final_colors = None
            for i in range(n_run_times):
                start_time = time.perf_counter()
                processed_image = run_algorithm(algo, original_image, current_colors)
                end_time = time.perf_counter()

                if processed_image is None:
                    break 
                
                mae, mse = calculate_error_metrics(original_image, processed_image)
                
                
                if i == 0:  
                    final_output_path = output_base / algo / f"color_{current_colors}" / f"{clean_name}.png"
                                        
                    save_image_output(processed_image, final_output_path)
                    final_colors = get_image_color_count(final_output_path)

                time_taken = end_time - start_time

                rows.append({
                    'Image Name': clean_name,
                    'Resolution': resolution,
                    'Algorithm': algo,
                    'Target Colors': current_colors, 
                    'Original Colors': original_colors,
                    'Final Colors': final_colors,
                    'Time Taken (ms)': time_taken * 1000,
                    'MAE': mae,
                    'MSE': mse
                })
            
            current_colors *= 2

    results = pd.DataFrame(rows)
    
    if output_csv_path.exists():
        results.to_csv(output_csv_path, mode='a', header=False, index=False)
    else:
        results.to_csv(output_csv_path, mode='w', header=True, index=False)

def generate_statistics_charts():    
    stat_path = OUTPUT_STATS_DIR / "image_charts"
    stat_path.mkdir(parents=True, exist_ok=True)

    csv_file = OUTPUT_CSV_DIR / "benchmark_stats_final.csv"
    if not csv_file.exists():
        print(f"Error: CSV file '{csv_file}' not found. Please run the benchmark first.")
        return
    
    df = pd.read_csv(csv_file)

    L = 255.0
    df['PSNR'] = np.where(
        df['MSE'] > 0, 
        20 * np.log10(L / np.sqrt(df['MSE'])), 
        100 
    )

    unique_images = df['Image Name'].unique()
    print(f"Found {len(unique_images)} unique images. Generating charts...")

    for img_name in unique_images:
        img_df = df[df['Image Name'] == img_name]

        avg_df = img_df.groupby(['Target Colors', 'Algorithm'])[['MAE', 'MSE', 'PSNR', 'Time Taken (ms)']].mean().reset_index()

        pivot_mae = avg_df.pivot(index='Target Colors', columns='Algorithm', values='MAE')
        pivot_mse = avg_df.pivot(index='Target Colors', columns='Algorithm', values='MSE')
        pivot_psnr = avg_df.pivot(index='Target Colors', columns='Algorithm', values='PSNR')
        pivot_time = avg_df.pivot(index='Target Colors', columns='Algorithm', values='Time Taken (ms)')

        plt.style.use('seaborn-v0_8-whitegrid')
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        colors = plt.cm.tab10.colors

        pivot_mae.plot(kind='bar', ax=axes[0, 0], color=colors, legend=False, width=0.8)
        axes[0, 0].set_title('Avg. MAE', pad=15)
        axes[0, 0].tick_params(axis='x', rotation=0)

        pivot_mse.plot(kind='bar', ax=axes[0, 1], color=colors, legend=False, width=0.8)
        axes[0, 1].set_title('Avg. MSE', pad=15)
        axes[0, 1].tick_params(axis='x', rotation=0)

        pivot_psnr.plot(kind='bar', ax=axes[1, 0], color=colors, legend=False, width=0.8)
        axes[1, 0].set_title('Avg. PSNR', pad=15)
        axes[1, 0].tick_params(axis='x', rotation=0)

        pivot_time.plot(kind='bar', ax=axes[1, 1], color=colors, legend=False, width=0.8)
        axes[1, 1].set_title('Avg. time (ms)', pad=15)
        axes[1, 1].tick_params(axis='x', rotation=0)

        for ax in axes.flatten():
            ax.set_xlabel('')
            ax.grid(axis='y', linestyle='--', alpha=0.7)
            ax.grid(axis='x', visible=False)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

        fig.suptitle(f'Performance Metrics: {img_name}', fontsize=16, fontweight='bold', y=1.02)

        handles, labels = axes[0, 0].get_legend_handles_labels()
        fig.legend(
            handles, labels, loc='lower center', ncol=min(len(labels), 7), 
            bbox_to_anchor=(0.5, -0.05), frameon=False, handletextpad=0.5
        )

        plt.tight_layout()
        
        safe_name = Path(img_name).stem 
        output_file = stat_path / f"{safe_name}_comparison_charts.png"
        
        plt.savefig(output_file, bbox_inches='tight', dpi=300)
        plt.close()

        print(f"Generated: {output_file.name}")

    print("--- All Statistics Generated Successfully ---")
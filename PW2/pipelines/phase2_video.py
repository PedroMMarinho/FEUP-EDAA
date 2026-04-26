import cv2
import time
from pathlib import Path
import numpy as np
from core.algorithm import run_algorithm
from utils.macros import OUTPUT_VIDEO_DIR 

def process_video(input_path: str | Path, target_colors: int) -> None:
    input_file = Path(input_path)
    if not input_file.exists():
        print(f"Error: Video {input_path} not found.")
        return

    out_dir = OUTPUT_VIDEO_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = out_dir / f"{input_file.stem}_quantized_{target_colors}.mp4"

    print(f"--- Processing Video: {input_file.name} ---")
    
    cap = cv2.VideoCapture(str(input_path))
    
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    start_time = time.time()
    frame_count = 0

    print(f"Total Frames to process: {total_frames} @ {fps} FPS")
    algo = "Octree-SOM"  
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break 
        
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        processed_rgb = run_algorithm(algo, frame_rgb, target_colors) 
        
        processed_bgr = cv2.cvtColor(processed_rgb, cv2.COLOR_RGB2BGR)
        
        out.write(processed_bgr)    
        frame_count += 1
        
        if frame_count % 30 == 0:
            print(f"Processed {frame_count}/{total_frames} frames...")

    cap.release()
    out.release()
    
    elapsed_time = time.time() - start_time
    print(f"--- Video Processing Complete ---")
    print(f"Saved to: {output_path}")
    print(f"Time taken: {elapsed_time:.2f} seconds")
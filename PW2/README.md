# Real-Time Color Quantization Using Octree Structures

This project implements and evaluates several color quantization algorithms for static images, videos, live camera input, and live screen/game capture. The main goal is to compare the trade-off between visual quality, execution time, and real-time usability, with a particular focus on Octree-based quantization.

The work was developed for the second practical assignment of **Advanced Data Structures and Algorithms**.

## Authors

* Tuomas Haapasalo
* Pedro Marinho
* Miguel Mateus

## Project Overview

Color quantization reduces the number of distinct colors used to represent an image or video frame. This can reduce memory usage, bandwidth, and processing cost, but it also introduces a loss in visual quality. The project compares simple, classical, iterative, and hybrid quantization methods to understand which algorithms are most suitable for different practical scenarios.

The implementation supports four main phases:

1. **Static image quantization**
   Quantizes one image or a directory of images and records benchmark results.

2. **Video quantization**
   Reads a video file frame by frame, applies quantization, and writes the processed video.

3. **Live camera quantization**
   Applies quantization to a webcam stream in real time.

4. **Live game/screen capture integration**
   Captures an application window, applies quantization, and displays the processed result as a real-time overlay or virtual camera output.

## Implemented Algorithms

The main benchmark compares the following algorithms:

* **Uniform Quantization**
* **Median-Cut**
* **K-Means**
* **Self-Organizing Map (SOM)**
* **Octree-Baseline**
* **Octree-Euclidean**
* **Octree-K-Means**
* **Octree-SOM**

Additional practical components are also included:

* **Shader-Acerola / palette-based shader stylization** for artistic real-time effects.
* **Octree-Live** as an experimental live-processing optimization that reuses an Octree palette across several frames.

## Implementation Structure

The project is divided into a Python control layer and a C++ performance layer.

Python is used for:

* loading images and videos,
* managing the command-line interface,
* running the different phases,
* saving processed outputs,
* computing error metrics,
* generating benchmark CSV files and charts.

Most custom pixel-level algorithms are implemented in C++ and exposed to Python through `ctypes`. Median-Cut is implemented separately using PIL's built-in quantization method.

## Repository Structure

```text
PW2/
├── assets/
│   ├── input/                  # Input images and videos
│   └── output/                 # Generated images, videos, CSVs, and charts
├── core/
│   ├── algorithm.py            # Python wrappers for all algorithms
│   ├── cpp/octree.cpp          # C++ quantization implementations
│   └── py/                     # Python Octree prototype code
├── pipelines/
│   ├── phase1_image.py         # Static image and batch benchmarking
│   ├── phase2_video.py         # Video quantization
│   ├── phase3_camera.py        # Live camera quantization
│   └── phase4_game.py          # Live game/screen capture integration
├── palletes/                   # Custom color palettes for shader mode
├── utils/                      # Shared constants, utilities, and palette helpers
├── main.py                     # Main command-line entry point
├── Makefile                    # Build and execution shortcuts
├── requirements.txt            # Python dependencies
└── EDAA-PW2.pdf                # Assignment statement
```

## Requirements

### Python

Install Python dependencies with:

```bash
pip install -r requirements.txt
```

### C++ Compiler

The Octree and other performance-critical routines are compiled into a shared library.

On Linux/macOS, a C++ compiler such as `g++` is required. On Windows, a compatible compiler such as MinGW-w64 can be used.

## Setup

From inside the `PW2` directory, install dependencies and build the C++ library:

```bash
pip install -r requirements.txt
make build
```

The build creates one of the following files depending on the operating system:

```text
core/cpp/octree_lib.so    # Linux/macOS
core/cpp/octree_lib.dll   # Windows
```

This file is loaded by Python through `ctypes`, so the project must be built before running the Python scripts.

## Usage

All commands should be run from the `PW2` directory.

### Build the C++ Library

```bash
make build
```

### Phase 1: Single Image Quantization

```bash
make phase1 IMG=assets/input/raw_images/single_image/woods_1920x1080.png COLORS=256
```

Equivalent direct command:

```bash
python main.py --phase 1 --input assets/input/raw_images/single_image/woods_1920x1080.png --colors 256
```

### Phase 1: Batch Image Quantization

```bash
make phase1-all DIR=assets/input/raw_images/test_set/ COLORS=256
```

Equivalent direct command:

```bash
python main.py --phase 1 --input assets/input/raw_images/test_set/ --colors 256
```

### Generate Statistics Charts

After running benchmarks, charts can be generated from a CSV file in `assets/output/csv/`:

```bash
make phase1-stats CSV=benchmark_stats_1.csv
```

Equivalent direct command:

```bash
python main.py --phase 1 --stats --input benchmark_stats_1.csv
```

### Phase 2: Video Quantization

```bash
make phase2 VID=assets/input/raw_videos/test_set/foreman_cif.y4m COLORS=64
```

Equivalent direct command:

```bash
python main.py --phase 2 --input assets/input/raw_videos/test_set/foreman_cif.y4m --colors 64
```

### Phase 3: Live Camera Quantization

```bash
make phase3
```

Equivalent direct command:

```bash
python main.py --phase 3
```

This opens a live camera interface where the algorithm, target number of colors, and resolution can be changed during execution.

### Phase 4: Live Game / Screen Capture Integration

```bash
make phase4
```

Equivalent direct command:

```bash
python main.py --phase 4
```

This mode captures a selected application window and applies the selected quantization algorithm in real time. Some dependencies for this phase, such as `dxcam`, `pygetwindow`, and `pyvirtualcam`, are mainly intended for Windows.

## Output Files

Generated outputs are written under `assets/output/`:

```text
assets/output/modified_images/     # Quantized image outputs
assets/output/modified_videos/     # Quantized video outputs
assets/output/csv/                 # Benchmark CSV files
assets/output/statistics/          # Generated charts and FPS summaries
```

## Evaluation Metrics

The project evaluates algorithms using:

* **Execution time** in milliseconds,
* **MAE**: Mean Absolute Error,
* **MSE**: Mean Squared Error,
* **SSIM**: Structural Similarity Index Measure,
* **FPS** for live camera and game capture experiments,
* **Trade-off score** combining normalized runtime and normalized SSIM.

The trade-off score is computed per scenario, where each scenario is defined by one resolution and one target color count. Lower trade-off scores indicate a better balance between speed and visual quality.

## Summary of Results

The experiments show that no single algorithm is best in every category:

* **SOM** and **K-Means** generally provide the highest visual quality, but are too slow for real-time use at high resolutions.
* **Uniform Quantization** is the fastest method and can exceed the 60 FPS target in live game capture, but has the weakest visual quality.
* **Octree-based methods** provide the best practical compromise between quality and performance.
* **Octree-Baseline** is the strongest overall choice when both speed and visual quality are considered.

## Cleaning Outputs

To remove generated image outputs:

```bash
make clean
```

## Notes

* Run commands from inside the `PW2` directory so that relative paths resolve correctly.
* Rebuild the C++ library after modifying `core/cpp/octree.cpp`.
* Live game/screen capture functionality is platform-dependent and was primarily developed for Windows.
* Some output folders may be created automatically when running the scripts.

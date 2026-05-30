# Default variables 
IMG ?= assets/input/raw_images/sipi/4.2.03.tiff
VID ?= assets/input/raw_videos/test_set/foreman_cif.y4m
DIR ?= assets/input/raw_images/test_set/
CSV ?= benchmark_stats_final_v2.csv
COLORS ?= 256

# Compiler settings
CXX = g++
CXXFLAGS = -O3 -march=native -funroll-loops -ffast-math -shared -fPIC -fopenmp
ifeq ($(OS),Windows_NT)
    LIB_OUT = core/cpp/octree_lib.dll
    RM = del /Q /F
else
    LIB_OUT = core/cpp/octree_lib.so
    RM = rm -f
endif
SRC = core/cpp/octree.cpp

all: build

build: $(SRC)
	@echo "Compiling C++ Octree library..."
	$(CXX) $(CXXFLAGS) -o $(LIB_OUT) $(SRC)

phase1:
	@echo "Running Phase 1 (Single Image)..."
	python main.py --phase 1 --input $(IMG) --colors $(COLORS)

phase1-all:
	@echo "Running Phase 1 (Batch Directory)..."
	python main.py --phase 1 --input $(DIR) --colors $(COLORS)

phase1-stats:
	@echo "Generating statistical plots..."
	python main.py --phase 1 --stats --input $(CSV)

phase2:
	@echo "Running Phase 2 (Video Quantization)..."
	python main.py --phase 2 --input $(VID) --colors $(COLORS)

phase3:
	@echo "Running Phase 3 (Live Camera Quantization)..."
	python main.py --phase 3

phase4:
	@echo "Running Phase 4 (Performance Analysis)..."
	python main.py --phase 4

clean:
	@echo "Cleaning output directory..."
	rm -f assets/output/*.png
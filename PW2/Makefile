# Default variables 
IMG ?= assets/input/raw_images/sipi/4.2.03.tiff
DIR ?= assets/input/raw_images/test_set/
COLORS ?= 256

# Compiler settings
CXX = g++
CXXFLAGS = -O3 -march=native -funroll-loops -ffast-math -shared -fPIC -fopenmp
LIB_OUT = core/cpp/octree_lib.so
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

clean:
	@echo "Cleaning output directory..."
	rm -f assets/output/*.png
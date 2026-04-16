# Default variables 
IMG ?= assets/input/raw_images/sipi/4.2.03.tiff
DIR ?= assets/input/raw_images/
COLORS ?= 256

phase1:
	@echo "Running Phase 1 (Single Image)..."
	python main.py --phase 1 --input $(IMG) --colors $(COLORS)

phase1-all:
	@echo "Running Phase 1 (Batch Directory)..."
	python main.py --phase 1 --input $(DIR) --colors $(COLORS)

clean:
	@echo "Cleaning output directory..."
	rm -f assets/output/*.png
import random
from pathlib import Path
import numpy as np
from utils.macros import PALLETES_DIR

# ==========================================
# 1. HARDCODED CLASSICS
# ==========================================
PALETTES = {
    "Gameboy": np.array([
        [15, 56, 15], [48, 98, 48], [139, 172, 15], [155, 188, 15]    
    ], dtype=np.uint8),

    "Pico-8": np.array([
        [0, 0, 0], [29, 43, 83], [126, 37, 83], [0, 135, 81],
        [171, 82, 54], [95, 87, 79], [194, 195, 199], [255, 241, 232],
        [255, 0, 77], [255, 163, 0], [255, 236, 39], [0, 228, 54],
        [41, 173, 255], [131, 118, 156], [255, 119, 168], [255, 204, 170]
    ], dtype=np.uint8),

    "DB_32": np.array([
        [0, 0, 0], [34, 32, 52], [69, 40, 60], [102, 57, 49],
        [143, 86, 59], [223, 113, 38], [217, 160, 102], [238, 195, 154],
        [251, 242, 54], [153, 229, 80], [106, 190, 48], [55, 148, 110],
        [75, 105, 47], [82, 75, 36], [50, 60, 57], [63, 63, 116],
        [48, 96, 130], [91, 110, 225], [99, 155, 255], [95, 205, 228],
        [203, 219, 252], [255, 255, 255], [155, 173, 183], [132, 126, 135],
        [105, 106, 106], [89, 86, 82], [118, 66, 138], [172, 50, 50],
        [217, 87, 99], [215, 123, 186], [143, 151, 74], [138, 111, 48]
    ], dtype=np.uint8)
}

# ==========================================
# 2. THE AUTO-LOADER LOGIC
# ==========================================

def _load_hex_palette(filepath: Path) -> np.ndarray:
    """Reads a .hex file, converts to RGB, and sorts by luminance."""
    colors = []
    
    with open(filepath, 'r') as f:
        for line in f:
            hex_str = line.strip()
            if not hex_str: continue
            
            if hex_str.startswith('#'):
                hex_str = hex_str[1:]
            elif len(hex_str) == 8 and hex_str.upper().startswith('FF'):
                hex_str = hex_str[2:]
                
            try:
                r = int(hex_str[0:2], 16)
                g = int(hex_str[2:4], 16)
                b = int(hex_str[4:6], 16)
                colors.append([r, g, b])
            except ValueError:
                continue 
            
    palette_array = np.array(colors, dtype=np.uint8)
    
    luminance = (0.299 * palette_array[:, 0] + 
                 0.587 * palette_array[:, 1] + 
                 0.114 * palette_array[:, 2])
    sorted_indices = np.argsort(luminance)
    
    return palette_array[sorted_indices]

def init_directory_palettes():
    if not PALLETES_DIR.exists():
        PALLETES_DIR.mkdir(parents=True, exist_ok=True)
        print(f"🎨 Created directory '{PALLETES_DIR}'. Drop .hex files in here!")
        return

    loaded_count = 0
    for hex_file in PALLETES_DIR.glob("*.hex"):
        palette_name = hex_file.stem 
        try:
            PALETTES[palette_name] = _load_hex_palette(hex_file)
            loaded_count += 1
        except Exception as e:
            print(f"⚠️ Failed to load palette {hex_file.name}: {e}")
            
    if loaded_count > 0:
        print(f"🎨 Successfully loaded {loaded_count} custom palettes from '{PALLETES_DIR}'!")



def get_palette(name: str) -> np.ndarray:
    """Returns a specific palette by its exact name."""
    if name in PALETTES:
        return PALETTES[name]
    available = ", ".join(PALETTES.keys())
    raise ValueError(f"Palette '{name}' not found. Available: {available}")

def get_random_palette(target_colors: int = None) -> np.ndarray:
    """Returns a random palette. Can filter by exact color count."""
    available_names = list(PALETTES.keys())

    if target_colors is not None:
        available_names = [name for name in available_names if len(PALETTES[name]) == target_colors]
        if not available_names:
            raise ValueError(f"No {target_colors}-color palettes found!")

    chosen_name = random.choice(available_names)
    print(f"🎨 Using Palette: {chosen_name} ({len(PALETTES[chosen_name])} colors)")
    return PALETTES[chosen_name]
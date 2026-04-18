import numpy as np
from PIL import Image
from core.octree import Octree

def run_algorithm(algo: str, image_path: str, target_colors: int) -> Image.Image:
    print(f"Running {algo} algorithm with target colors: {target_colors}")
    match algo:
        case "Octree-Baseline":
            return octree_baseline(image_path, target_colors)
        case "Greedy":
            return None
        case "Median-Cut":
            return None
        case "K-Means":
            return None
        case "Uniform":
            return None
        case _:
            raise ValueError(f"Unknown algorithm: {algo}")

def octree_baseline(image_path: str, target_colors: int) -> Image.Image:
    img = Image.open(image_path).convert('RGB')
    pixels = np.array(img, dtype=int)
    height, width, _ = pixels.shape

    octree = Octree(max_depth=8)

    for y in range(height):
        for x in range(width):
            r, g, b = pixels[y, x]
            octree.insert(r, g, b)

            while octree.leaf_count > target_colors:
                octree.reduce_tree()

    while octree.leaf_count > target_colors:
        octree.reduce_tree()

   
    new_pixels = np.zeros_like(pixels)
    
    for y in range(height):
        for x in range(width):
            r, g, b = pixels[y, x]
            new_color = octree.get_mapped_color(r, g, b) 
            
            new_pixels[y, x] = [int(new_color[0]), int(new_color[1]), int(new_color[2])]

    return Image.fromarray(new_pixels.astype('uint8'), 'RGB')
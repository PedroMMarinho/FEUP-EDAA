from PIL import Image
import csv
from utils.macros import CSV_FILE

def load_image_data(filepath):
    img = Image.open(filepath).convert('RGB')
    width, height = img.size
    pixels = list(img.getdata()) 
    return width, height, pixels

def save_output(image, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    print(f"Saved output to: {output_path}")


def save_to_csv(image_name, resolution, algorithm, target_colors, original_colors, final_colors, time_taken):
    CSV_FILE.parent.mkdir(parents=True, exist_ok=True)

    file_exists = CSV_FILE.is_file()
    with open(CSV_FILE, mode='a', newline='') as csvfile:
        fieldnames = [
                    'Image Name', 'Resolution', 'Algorithm', 
                    'Target Colors', 'Original Colors', 'Final Colors', 'Time Taken (s)'
                ]       
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        writer.writerow({
                'Image Name': image_name,
                'Resolution': resolution,       
                'Algorithm': algorithm,
                'Target Colors': target_colors,
                'Original Colors': original_colors,
                'Final Colors': final_colors,
                'Time Taken (s)': round(time_taken, 4) 
            })

def get_image_resolution(image_path):
    img = Image.open(image_path)
    return img.size

def get_image_color_count(image_path):
    img = Image.open(image_path).convert('RGB')
    colors = img.getcolors(maxcolors=10000000) 
    return len(colors) 
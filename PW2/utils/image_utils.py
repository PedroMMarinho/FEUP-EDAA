from PIL import Image

def load_image_data(filepath):
    img = Image.open(filepath).convert('RGB')
    width, height = img.size
    pixels = list(img.getdata()) 
    return width, height, pixels

def save_output(image, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    print(f"Saved output to: {output_path}")
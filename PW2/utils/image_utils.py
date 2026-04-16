from PIL import Image

def load_image_data(filepath):
    img = Image.open(filepath).convert('RGB')
    width, height = img.size
    pixels = list(img.getdata()) 
    return width, height, pixels

def save_image_data(pixels, width, height, output_filepath):
    img = Image.new('RGB', (width, height))
    img.putdata(pixels)
    img.save(output_filepath)
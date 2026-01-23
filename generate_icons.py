"""
Generate PWA icons from source image.
Requires: pip install Pillow
"""

from PIL import Image
import os

def generate_pwa_icons(source_path: str, output_dir: str = "assets"):
    """Generate PWA icons in required sizes."""
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Open source image
    img = Image.open(source_path)
    
    # Ensure RGBA
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    sizes = {
        'icon-72.png': 72,
        'icon-96.png': 96,
        'icon-128.png': 128,
        'icon-144.png': 144,
        'icon-152.png': 152,
        'icon-192.png': 192,
        'icon-384.png': 384,
        'icon-512.png': 512,
    }
    
    for filename, size in sizes.items():
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        output_path = os.path.join(output_dir, filename)
        resized.save(output_path, 'PNG', optimize=True)
        print(f"Created: {output_path}")
    
    # Generate maskable icon (with padding)
    maskable_size = 512
    padding = int(maskable_size * 0.1)  # 10% padding for safe zone
    inner_size = maskable_size - (padding * 2)
    
    # Create new image with padding
    maskable = Image.new('RGBA', (maskable_size, maskable_size), (5, 10, 24, 255))  # bg color
    inner = img.resize((inner_size, inner_size), Image.Resampling.LANCZOS)
    maskable.paste(inner, (padding, padding), inner)
    
    maskable_path = os.path.join(output_dir, 'icon-maskable.png')
    maskable.save(maskable_path, 'PNG', optimize=True)
    print(f"Created: {maskable_path}")
    
    print("\n✅ All PWA icons generated!")

if __name__ == "__main__":
    generate_pwa_icons("assets/hyperionx_icon.png", "static")
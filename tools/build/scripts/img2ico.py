import os
import sys
from PIL import Image

def main():
    if len(sys.argv) < 3:
        print("Usage: python img2ico.py <image_file> <icon_file>")
        sys.exit(1)

    image_file = sys.argv[1]
    icon_file  = sys.argv[2]
    icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

    if not os.path.isfile(image_file):
        print(f"❌ ERROR: File '{image_file}' not found.")
        sys.exit(2)

    try:
        img = Image.open(image_file)
        img.save(icon_file, format='ICO', sizes=icon_sizes)
        print(f"✅ Icon saved: {icon_file}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        sys.exit(3)

if __name__ == "__main__":
    main()
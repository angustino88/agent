import os
import re
import sys
import subprocess


def clean_svg_file(svg_file):
    with open(svg_file, "r", encoding="utf-8") as f:
        svg = f.read()

    svg = re.sub(r'\s*<path[^>]*d="\s*"[^>]*/?>\s*', '\n', svg)

    with open(svg_file, "w", encoding="utf-8") as f:
        f.write(svg)

def image_to_svg(input_file, output_file, vtrace_exe):
    print(f"🔄 Processing: {os.path.basename(input_file)}")
    result = subprocess.run([
        vtrace_exe,
        "-i", input_file,
        "-o", output_file,
        "--colormode", "color",
        "--color_precision", "8",
        "--gradient_step", "4",
        "--hierarchical", "cutout",
        "--mode", "spline",
        "--path_precision", "8",
        "--corner_threshold", "30",
        "--segment_length", "3.5",
        "--splice_threshold", "25",
        "--filter_speckle", "1"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if result.returncode != 0:
        print(f"❌ ERROR: Conversion failed for {input_file}")
        return False
    clean_svg_file(output_file)
    return True

def main():
    supported_exts = [".png", ".jpg", ".jpeg", ".bmp", ".gif"]

    if len(sys.argv) < 4:
        print("Usage:")
        print("  python img2svg.py <vtracer_exe> <image_dir / image_file> <svg_dir> ")
        sys.exit(1)

    vtrace_exe = sys.argv[1]
    image_path = sys.argv[2]
    svg_dir    = sys.argv[3]

    os.makedirs(svg_dir, exist_ok=True)

    print("===========================================")
    print("🖌️  Starting image to SVG conversion...")
    print(f"📂 Target directory: {os.path.abspath(svg_dir)}")
    print("===========================================")

    error_occurred = False

    if os.path.isdir(image_path):
        print(f"📁 Source directory: {os.path.abspath(image_path)}")
        for filename in os.listdir(image_path):
            input_file = os.path.join(image_path, filename)
            ext = os.path.splitext(filename)[1].lower()
            output_file = os.path.join(svg_dir, os.path.splitext(filename)[0] + ".svg")
            if ext in supported_exts:
                if not image_to_svg(input_file, output_file, vtrace_exe):
                    error_occurred = True
                    break
            elif ext == ".svg":
                copied_file = os.path.join(svg_dir, filename)
                try:
                    import shutil
                    shutil.copy2(input_file, copied_file)
                    clean_svg_file(copied_file)
                    print(f"📄 Copied SVG file: {filename}")
                except Exception as e:
                    print(f"❌ ERROR: Could not copy {filename}: {e}")
                    error_occurred = True
                    break
    elif os.path.isfile(image_path):
        print(f"📄 Input file: {os.path.abspath(image_path)}")
        output_file = os.path.join(svg_dir, os.path.splitext(os.path.basename(image_path))[0] + ".svg")
        if not image_to_svg(image_path, output_file, vtrace_exe):
            error_occurred = True
    else:
        print(f"❌ ERROR: Path '{image_path}' not found.")
        error_occurred = True

    print("===========================================")
    if not error_occurred:
        print("✅ Image to SVG conversion complete.")

if __name__ == "__main__":
    main()
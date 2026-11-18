import os
import sys
import subprocess

def main():
    if len(sys.argv) < 4:
        print("Usage:")
        print("  python qrc2py.py <pyrcc6_exe> <qrc_dir / qrc_file> <py_dir>")
        sys.exit(1)

    PYRCC6_EXE     = sys.argv[1]
    QRC_INPUT_PATH = sys.argv[2]
    PY_OUTPUT_DIR  = sys.argv[3]

    os.makedirs(PY_OUTPUT_DIR, exist_ok=True)
    print("===========================================")
    print("🎨 Starting QRC to PY conversion...")
    print(f"📂 Target directory: {os.path.abspath(PY_OUTPUT_DIR)}")
    print("===========================================")

    if os.path.isdir(QRC_INPUT_PATH):
        # Batch mode
        print(f"📁 Source directory: {os.path.abspath(QRC_INPUT_PATH)}")
        error_occurred = False
        for filename in os.listdir(QRC_INPUT_PATH):
            if filename.endswith(".qrc"):
                qrc_file = os.path.join(QRC_INPUT_PATH, filename)
                py_file = os.path.join(PY_OUTPUT_DIR, os.path.splitext(filename)[0] + ".py")
                print(f"🔄 Processing: {filename}")
                result = subprocess.run([PYRCC6_EXE, qrc_file, "-o", py_file])
                if result.returncode != 0:
                    print(f"❌ ERROR: Conversion failed for {filename}")
                    error_occurred = True
                    break
        print("===========================================")
        if not error_occurred:
            print("✅ All .qrc files have been converted.")

    elif os.path.isfile(QRC_INPUT_PATH):
        # Single file mode
        print(f"📄 Input file: {os.path.abspath(QRC_INPUT_PATH)}")
        py_file = os.path.join(PY_OUTPUT_DIR, os.path.splitext(os.path.basename(QRC_INPUT_PATH))[0] + ".py")
        print(f"📂 Target directory: {os.path.abspath(PY_OUTPUT_DIR)}")
        print("===========================================")
        result = subprocess.run([PYRCC6_EXE, QRC_INPUT_PATH, "-o", py_file])
        if result.returncode != 0:
            print(f"❌ ERROR: Conversion failed for {os.path.basename(QRC_INPUT_PATH)}")
        else:
            print(f"✅ Successfully converted {QRC_INPUT_PATH} to {py_file}")
    else:
        print(f"❌ ERROR: Path '{QRC_INPUT_PATH}' not found.")
        sys.exit(1)

if __name__ == "__main__":
    main()
import os
import sys
import subprocess

def main():
    if len(sys.argv) >= 3:
        QTDESIGNER_EXE = sys.argv[1]
        UI_INPUT_PATH  = sys.argv[2]
        print(f"🖌️  Qt Designer: {QTDESIGNER_EXE}")
        print(f"📁 UI Path: {UI_INPUT_PATH}")
        if os.path.isdir(UI_INPUT_PATH):
            ui_files = []
            for root, dirs, files in os.walk(UI_INPUT_PATH):
                for file in files:
                    if file.endswith(".ui"):
                        full_path = os.path.abspath(os.path.join(root, file))
                        ui_files.append(full_path)
                        print(f"📄 Found: {full_path}")
            if ui_files:
                print(f"🚀 Launching Qt Designer with {len(ui_files)} UI files...")
                subprocess.run([QTDESIGNER_EXE] + ui_files)
            else:
                print("⚠️  No .ui files found.")
        elif os.path.isfile(UI_INPUT_PATH):
            ui_file = os.path.abspath(UI_INPUT_PATH)
            print(f"🚀 Opening: {ui_file}")
            subprocess.run([QTDESIGNER_EXE, ui_file])
        else:
            print(f"❌ ERROR: Path '{UI_INPUT_PATH}' not found.")
    else:
        print("Usage:")
        print("  python qtdesigner.py [designer_exe] <ui_dir / ui_file> ")

if __name__ == "__main__":
    main()
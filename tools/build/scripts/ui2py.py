import os
import sys
import subprocess

def pach_resource_import(py_file, target_import):
    # Strip surrounding quotes if the variable was defined with them
    target = target_import
    if (target.startswith('"') and target.endswith('"')) or (target.startswith("'") and target.endswith("'")):
        target = target[1:-1]

    # Determine candidate names to look for in existing imports (e.g. resources, resources_rc)
    candidates = []
    try:
        tok = target.strip().split()
        if len(tok) >= 4 and tok[0] == 'from' and tok[2] == 'import':
            base = tok[3]
            candidates = [base, base + '_rc']
        elif len(tok) >= 2 and tok[0] == 'import':
            base = tok[1]
            candidates = [base, base + '_rc']
    except Exception:
        candidates = []

    with open(py_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    replaced = False
    for i, line in enumerate(lines):
        for cand in candidates:
            if f"import {cand}" in line or f"from {cand} import" in line or (cand in line and 'import' in line):
                lines[i] = target + "\n"
                replaced = True
                print(f"Patched resource import in {os.path.basename(py_file)}")
                break
        if replaced:
            break

    if not replaced:
        insert_index = 0
        for i, line in enumerate(lines):
            if line.startswith("import") or line.startswith("from "):
                insert_index = i + 1
            else:
                break
        lines.insert(insert_index, target + "\n")

    with open(py_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)

def main():
    if len(sys.argv) < 4:
        print("Usage:")
        print("  python ui2py.py <pyuic_exe> <ui_dir / ui_file> <py_dir> [resource_import]")
        sys.exit(1)

    PYUIC_EXE       = sys.argv[1]
    UI_INPUT_PATH   = sys.argv[2]
    PY_OUTPUT_DIR   = sys.argv[3]
    RESOURCE_IMPORT = sys.argv[4] if len(sys.argv) > 4 else ""
    os.makedirs(PY_OUTPUT_DIR, exist_ok=True)
    print("===========================================")
    print("Starting UI-to-Python conversion...")
    if os.path.isdir(UI_INPUT_PATH):
        print(f"Source directory: {os.path.abspath(UI_INPUT_PATH)}")
        error_occurred = False
        for filename in os.listdir(UI_INPUT_PATH):
            if filename.endswith(".ui"):
                ui_file = os.path.join(UI_INPUT_PATH, filename)
                py_file = os.path.join(PY_OUTPUT_DIR, os.path.splitext(filename)[0] + ".py")
                print(f"Processing: {filename}")
                result = subprocess.run([PYUIC_EXE, ui_file, "-o", py_file])
                if result.returncode != 0:
                    print(f"❌ ERROR: Conversion failed for {filename}")
                    error_occurred = True
                    break
                else:
                    if RESOURCE_IMPORT != "":
                        pach_resource_import(py_file, RESOURCE_IMPORT)
        print("===========================================")
        if not error_occurred:
            print("All .ui files have been converted.")
    elif os.path.isfile(UI_INPUT_PATH):
        print(f"Input file: {os.path.abspath(UI_INPUT_PATH)}")
        py_file = os.path.join(PY_OUTPUT_DIR, os.path.splitext(os.path.basename(UI_INPUT_PATH))[0] + ".py")
        print(f"Target directory: {os.path.abspath(PY_OUTPUT_DIR)}")
        print("===========================================")
        result = subprocess.run([PYUIC_EXE, UI_INPUT_PATH, "-o", py_file])
        if result.returncode != 0:
            print(f"❌ ERROR: Conversion failed for {os.path.basename(UI_INPUT_PATH)}")
        else:
            if RESOURCE_IMPORT != "":
                pach_resource_import(py_file, RESOURCE_IMPORT)
            print(f"Successfully converted {UI_INPUT_PATH} to {py_file}")
    else:
        print(f"❌ ERROR: Path '{UI_INPUT_PATH}' not found.")

if __name__ == "__main__":
    main()
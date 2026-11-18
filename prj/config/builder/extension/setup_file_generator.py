import os
from pathlib import Path

SETUP_FILE_NAME = 'setup.bat'
SETUP_TEMPLATE_PATH = os.path.join(str(Path(__file__).resolve().parent), SETUP_FILE_NAME)

def read_lines(file_path: str) -> list[str]:
    """Read all lines from a file and return as a list of strings."""
    with open(file_path, 'r') as file:
        return file.readlines()

def write_lines(lines: list[str], file_path: str) -> None:
    """Write each string in lines as a line to the file."""
    with open(file_path, 'w') as file:
        for line in lines:
            file.write(f"{line.rstrip()}\n")

def generate_setup_file(app_name: str, dest_dir: str) -> None:
    """
    Generate a setup.bat file for the given app_name in the destination directory.
    Replaces the first occurrence of 'APP_NAME' in the template with the actual app_name.
    """
    lines = read_lines(SETUP_TEMPLATE_PATH)
    for idx, line in enumerate(lines):
        if 'APP_NAME' in line:
            lines[idx] = line.replace('APP_NAME', app_name, 1)
            break
    dest_path = os.path.join(dest_dir, SETUP_FILE_NAME)
    write_lines(lines, dest_path)
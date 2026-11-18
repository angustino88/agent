import os
import shutil
import zipfile
from pathlib import Path
from typing import Optional

class ZipUtil:
    @staticmethod
    def zip_directory(src_dir: str, zip_file: str) -> None:
        """
        Zip an entire directory (including subdirectories and files).
        """
        with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(src_dir):
                for file in files:
                    full_path = os.path.join(root, file)
                    arcname = os.path.relpath(full_path, src_dir)
                    zipf.write(full_path, arcname)

    @staticmethod
    def unzip_all(zip_file: str, target_dir: str) -> None:
        """
        Extract all contents of a zip file to a target directory.
        """
        with zipfile.ZipFile(zip_file, 'r') as zipf:
            zipf.extractall(target_dir)

    @staticmethod
    def read_file(zip_file: str, relative_file: str, encoding: str = 'utf-8') -> Optional[str]:
        """
        Read the content of a file inside a zip archive.
        """
        try:
            with zipfile.ZipFile(zip_file, 'r') as zipf:
                return zipf.read(relative_file).decode(encoding)
        except Exception:
            return None

    @staticmethod
    def unzip_file(zip_file: str, relative_file: str, target_dir: str) -> Optional[str]:
        """
        Extract a single file from a zip archive, preserving folder structure.
        """
        with zipfile.ZipFile(zip_file, 'r') as zipf:
            zipf.extract(relative_file, path=target_dir)
        extracted_path = os.path.join(target_dir, relative_file)
        return extracted_path if os.path.exists(extracted_path) else None

    @staticmethod
    def unzip_file_flat(zip_file: str, relative_file: str, target_dir: str) -> Optional[str]:
        """
        Extract a single file from a zip archive to the target directory (no folder structure).
        """
        with zipfile.ZipFile(zip_file, 'r') as zipf:
            zipf.extract(relative_file, path=target_dir)
        extracted_path = os.path.join(target_dir, relative_file)
        flat_path = os.path.join(target_dir, os.path.basename(relative_file))
        if extracted_path != flat_path and os.path.exists(extracted_path):
            shutil.copyfile(extracted_path, flat_path)
            # Remove the extracted folder structure
            try:
                shutil.rmtree(os.path.join(target_dir, Path(relative_file).parts[0]))
            except Exception:
                pass
        return flat_path if os.path.exists(flat_path) else None

    @staticmethod
    def list_files(zip_file: str) -> list[str]:
        """
        List all files in a zip archive.
        """
        with zipfile.ZipFile(zip_file, 'r') as zipf:
            return zipf.namelist()

    @staticmethod
    def is_valid_zip(zip_file: str) -> bool:
        """
        Check if a file is a valid zip archive.
        """
        return zipfile.is_zipfile(zip_file)

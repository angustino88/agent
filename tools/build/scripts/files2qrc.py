import os
import sys

def main():
    if len(sys.argv) < 4:
        print("Usage: python files2qrc.py <resource_dir / resource_file> <prefix> <qrc_file> [--merge]")
        sys.exit(1)

    resource_path  = sys.argv[1]
    qrc_prefix     = sys.argv[2]
    qrc_file_path  = sys.argv[3]
    merge_flag     = "--merge" in sys.argv

    file_count = 0
    new_section = []

    if os.path.isdir(resource_path):
        icon_files = [
            os.path.join(resource_path, f)
            for f in os.listdir(resource_path)
            if os.path.isfile(os.path.join(resource_path, f))
        ]
    elif os.path.isfile(resource_path):
        icon_files = [resource_path]
    else:
        print(f"❌ Error: {resource_path} is not a valid directory or file.")
        sys.exit(2)

    new_section.append(f'  <qresource prefix="{qrc_prefix}">\n')
    for file_path in icon_files:
        new_section.append(f'    <file>{os.path.relpath(file_path, os.path.dirname(qrc_file_path))}</file>\n')
        file_count += 1
    new_section.append("  </qresource>\n")

    if merge_flag and os.path.exists(qrc_file_path):
        with open(qrc_file_path, "r", encoding="utf-8") as qrc:
            content = qrc.read()
        prefix_tag = f'<qresource prefix="{qrc_prefix}">'
        if prefix_tag in content:
            # Insert new files before closing tag of the correct prefix section
            lines = content.splitlines()
            new_files = [line.rstrip() for line in new_section if line.strip().startswith("<file")]
            updated_lines = []
            inside_prefix = False
            for line in lines:
                if line.strip() == prefix_tag:
                    inside_prefix = True
                    updated_lines.append(line)
                elif inside_prefix and line.strip() == "</qresource>":
                    # Insert new files before closing tag
                    updated_lines.extend(new_files)
                    updated_lines.append(line)
                    inside_prefix = False
                else:
                    updated_lines.append(line)
            # Remove closing </RCC> if present
            if updated_lines and updated_lines[-1].strip() == "</RCC>":
                updated_lines = updated_lines[:-1]
            # Remove any blank lines at the end
            while updated_lines and updated_lines[-1].strip() == "":
                updated_lines = updated_lines[:-1]
            with open(qrc_file_path, "w", encoding="utf-8") as qrc:
                qrc.write("\n".join(updated_lines))
                qrc.write("\n</RCC>\n")
            print(f"✅ Successfully appended {file_count} files to prefix '{qrc_prefix}' in {qrc_file_path}.")
        else:
            # Normal merge: add new section
            if content.strip().endswith("</RCC>"):
                content = content.strip()[:-6]
            else:
                print("⚠️ Warning: Existing QRC file does not end with </RCC>, merging anyway.")
            with open(qrc_file_path, "w", encoding="utf-8") as qrc:
                qrc.write(content)
                qrc.writelines(new_section)
                qrc.write("</RCC>\n")
            print(f"✅ Successfully merged {file_count} files into {qrc_file_path}.")
    else:
        with open(qrc_file_path, "w", encoding="utf-8") as qrc:
            qrc.write("<RCC>\n")
            qrc.writelines(new_section)
            qrc.write("</RCC>\n")
        print(f"✅ Successfully generated {qrc_file_path} with {file_count} files.")

if __name__ == "__main__":
    main()
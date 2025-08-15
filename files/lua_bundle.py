import os
import sys


def stack_lua_files(source_dir, output_file):
    lua_files = []
    for root, _, files in os.walk(source_dir):
        for file in files:
            if file.endswith(".lua"):
                full_path = os.path.join(root, file)
                lua_files.append(full_path)

    lua_files.sort()

    with open(output_file, "w", encoding="utf-8") as outfile:
        for file in lua_files:
            with open(file, "r", encoding="utf-8") as infile:
                outfile.write(f"-- {file}\n")
                outfile.write(infile.read())
                outfile.write("\n\n")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python stack_lua.py <source_dir> <output_file>")
        sys.exit(1)

    source_directory = sys.argv[1]
    output_path = sys.argv[2]

    if not os.path.isdir(source_directory):
        print(f"Error: '{source_directory}' is not a valid directory.")
        sys.exit(1)

    stack_lua_files(source_directory, output_path)

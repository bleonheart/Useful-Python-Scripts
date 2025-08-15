import argparse
import os


def stack_lua_files(source_dir, output_file):
    if not os.path.isdir(source_dir):
        print(f"Error: '{source_dir}' is not a valid directory.")
        return
    paths = []
    for root, _, files in os.walk(source_dir):
        for f in files:
            if f.endswith(".lua"):
                paths.append(os.path.join(root, f))
    paths.sort()
    with open(output_file, "w", encoding="utf-8") as out:
        for p in paths:
            with open(p, "r", encoding="utf-8-sig") as inp:
                out.write(f"-- {p}\n")
                out.write(inp.read())
                out.write("\n\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--source", default=os.getcwd())
    parser.add_argument("-o", "--output")
    args = parser.parse_args()
    out = args.output or os.path.join(args.source, "output.lua")
    stack_lua_files(args.source, out)

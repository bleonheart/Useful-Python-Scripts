import re

INPUT_PATH = "path/to/input_file.txt"
OUTPUT_PATH = "path/to/output_file.txt"


def remove_duplicates(input_path, output_path):
    pattern = re.compile(r'^\s*(?P<key>\[?"?[\w]+"?\]?)\s*=\s*".*",?')
    seen = set()
    removed = []
    output_lines = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            m = pattern.match(line)
            if m:
                key = m.group("key")
                if key in seen:
                    removed.append(key)
                    continue
                seen.add(key)
            output_lines.append(line)
    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(output_lines)
    for key in removed:
        print(f"removed duplicate entry: {key}")


if __name__ == "__main__":
    remove_duplicates(INPUT_PATH, OUTPUT_PATH)

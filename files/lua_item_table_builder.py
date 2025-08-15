import glob
import os
import re
import sys

folder_table = {
    "aid": r"E:\GMOD\Server\garrysmod\gamemodes\falloutrp\schema\aid",
    "junk": r"E:\GMOD\Server\garrysmod\gamemodes\falloutrp\schema\junk",
}


def extract_braced(text, start):
    count = 0
    for i, ch in enumerate(text[start:], start=start):
        if ch == "{":
            count += 1
        elif ch == "}":
            count -= 1
            if count == 0:
                return text[start : i + 1]
    return None


def extract_all_fields(text):
    fields = {}
    for m in re.finditer(r"ITEM\.(\w+)\s*=", text):
        name = m.group(1)
        idx = m.end()
        while idx < len(text) and text[idx].isspace():
            idx += 1
        if idx < len(text) and text[idx] == "{":
            value = extract_braced(text, idx)
        else:
            nl = text.find("\n", idx)
            nl = nl if nl != -1 else len(text)
            value = text[idx:nl].rstrip().rstrip(";")
        if value:
            fields[name] = value.strip()
    return fields


for alias, folder in folder_table.items():
    if not os.path.isdir(folder):
        sys.exit(f'Error: directory "{folder}" does not exist')
    paths = sorted(glob.glob(os.path.join(folder, "*.lua")))
    if not paths:
        sys.exit(f'Error: no .lua files found in "{folder}"')
    entries = []
    for path in paths:
        key = os.path.splitext(os.path.basename(path))[0]
        text = open(path, "r", encoding="utf-8").read()
        fields = extract_all_fields(text)
        normal = []
        tables = []
        for name in sorted(fields):
            v = fields[name]
            line = f'["{name}"] = {v}'
            if v.lstrip().startswith("{"):
                tables.append(line)
            else:
                normal.append(line)
        parts = normal + tables
        block = f'    ["{key}"] = {{\n        ' + ",\n        ".join(parts) + "\n    }"
        entries.append(block)
    table_text = "TableSample = {\n" + ",\n".join(entries) + "\n}\n"
    out = f"sh_{alias}.lua"
    try:
        with open(out, "w", encoding="utf-8") as f:
            f.write(table_text)
    except Exception as e:
        sys.exit(f'Error writing "{out}": {e}')
    print(f"Processed {len(entries)} items into {out}")

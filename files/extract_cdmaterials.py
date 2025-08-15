import json
import os
import sys

from srctools.filesys import FileSystemChain, RawFileSystem, get_filesystem
from srctools.mdl import Model

GMOD_DIR = r"D:\SteamLibrary\steamapps\common\GarrysMod\garrysmod"
DEFAULT_MODELS_ROOT = r"C:\Users\Administrator\Desktop\gay\models"
DEFAULT_OUTPUT_JSON = "cdmaterials.json"


def extract_cdmaterials(fs, name):
    mdl = Model(fs, fs[name])
    return getattr(mdl, "cdmaterials", [])


def find_cdmaterials(root):
    entries = []
    for base, _, files in os.walk(root):
        fs = FileSystemChain(RawFileSystem(base), get_filesystem(GMOD_DIR))
        for fn in files:
            if not fn.lower().endswith(".mdl"):
                continue
            full = os.path.join(base, fn)
            try:
                mats = extract_cdmaterials(fs, fn)
            except Exception as e:
                print(f"Error {full}: {e}", file=sys.stderr)
                mats = []
            entries.append(
                {
                    "model": full,
                    "materials": mats,
                }
            )
    return entries


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MODELS_ROOT
    out = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUTPUT_JSON
    data = find_cdmaterials(root)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(data)} entries to {out}")


if __name__ == "__main__":
    main()

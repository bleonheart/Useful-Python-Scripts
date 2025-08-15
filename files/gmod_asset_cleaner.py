import json
import os
from collections import Counter, defaultdict

import humanize
from srctools.filesys import FileSystemChain, RawFileSystem, get_filesystem
from srctools.mdl import Model

ROOT = r"C:\\Users\\Administrator\\Desktop\\gay"
GMOD_DIR = r"D:\\SteamLibrary\\steamapps\\common\\GarrysMod\\garrysmod"
SOUND_EXTS = {".wav", ".mp3", ".ogg", ".flac", ".aac"}
PARTICLE_EXTS = {".pcf"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tga", ".dds", ".bmp", ".gif"}
MATERIAL_EXTS = {".vmt", ".vtf"}
MODEL_EXTS = {".mdl", ".phy", ".vvd", ".vtx", ".dx90.vtx"}


def norm(path: str) -> str:
    return path.replace("\\", "/").lower()


def read_lua() -> str:
    parts = []
    for base, _, files in os.walk(ROOT):
        for fn in files:
            if fn.lower().endswith(".lua"):
                try:
                    with open(
                        os.path.join(base, fn), encoding="utf-8", errors="ignore"
                    ) as f:
                        parts.append(f.read())
                except Exception:
                    pass
    return norm("\n".join(parts))


def group_files():
    cats = {
        k: defaultdict(list)
        for k in ("sound", "particle", "image", "material", "model")
    }
    model_exts = sorted(MODEL_EXTS, key=lambda e: -len(e))
    for base, _, files in os.walk(ROOT):
        for fn in files:
            full = os.path.join(base, fn)
            rel = norm(os.path.relpath(full, ROOT))
            lower = fn.lower()
            ext_matched = next((e for e in model_exts if lower.endswith(e)), None)
            if ext_matched:
                cat = "model"
            else:
                ext = os.path.splitext(lower)[1]
                if ext in SOUND_EXTS:
                    cat = "sound"
                elif ext in PARTICLE_EXTS:
                    cat = "particle"
                elif ext in IMAGE_EXTS:
                    cat = "image"
                elif ext in MATERIAL_EXTS:
                    cat = "material"
                else:
                    continue
                ext_matched = ext
            if cat in ("sound", "particle", "image"):
                key = rel
            else:
                key = rel[: -len(ext_matched)]
            cats[cat][key].append(full)
    for cat, mapping in cats.items():
        print(f"{sum(len(v) for v in mapping.values())} {cat} files found")
    return cats


def find_unused_non_materials(lua_text: str, cats):
    unused = []
    removed = Counter()
    for name, paths in cats["sound"].items():
        if name not in lua_text:
            unused.extend(paths)
            removed["sound"] += len(paths)
    for name, paths in cats["particle"].items():
        if name not in lua_text:
            unused.extend(paths)
            removed["particle"] += len(paths)
    for name, paths in cats["image"].items():
        if name not in lua_text:
            unused.extend(paths)
            removed["image"] += len(paths)
    for key, paths in cats["model"].items():
        if key + ".mdl" not in lua_text:
            unused.extend(paths)
            removed["model"] += len(paths)
    for cat in ("sound", "particle", "image", "model"):
        print(f"{removed[cat]} {cat} files marked unused")
    return list(dict.fromkeys(unused)), removed


def delete_paths(paths):
    freed = 0
    for p in paths:
        try:
            freed += os.path.getsize(p)
            os.remove(p)
        except Exception:
            pass
    return freed


def clean_empty_dirs():
    removed = 0
    for base, dirs, files in os.walk(ROOT, topdown=False):
        if not dirs and not files:
            try:
                os.rmdir(base)
                removed += 1
            except OSError:
                pass
    return removed


def extract_cdmaterials():
    entries = []
    keep_dirs = set()
    for base, _, files in os.walk(ROOT):
        fs = FileSystemChain(RawFileSystem(base), get_filesystem(GMOD_DIR))
        for fn in files:
            if not fn.lower().endswith(".mdl"):
                continue
            try:
                cdm = Model(fs, fs[fn]).cdmaterials
            except Exception:
                cdm = []
            dirs = []
            for d in cdm:
                nd = norm(os.path.join("materials", d.strip("/\\")) + "/")
                dirs.append(nd)
                keep_dirs.add(nd)
            entries.append({"model": os.path.join(base, fn), "materials": dirs})
    print(f"{len(entries)} models processed for cdmaterials")
    return entries, keep_dirs


def find_unused_materials(lua_text: str, mats: dict, keep_dirs: set):
    unused = []
    removed = 0
    for _, paths in mats.items():
        for p in paths:
            rel = norm(os.path.relpath(p, ROOT))
            key = norm(os.path.splitext(rel)[0])
            if (
                not any(rel.startswith(d) for d in keep_dirs)
                and key + ".vmt" not in lua_text
                and key + ".vtf" not in lua_text
            ):
                unused.append(p)
                removed += 1
    print(f"{removed} material files marked unused")
    return list(dict.fromkeys(unused)), removed


def main():
    lua_text = read_lua()
    cats = group_files()
    unused_non_mat, removed_non_mat = find_unused_non_materials(lua_text, cats)
    size_non_mat = sum(os.path.getsize(p) for p in unused_non_mat)
    print(
        f"{len(unused_non_mat)} non‑material assets totalling {humanize.naturalsize(size_non_mat)}"
    )
    if (
        unused_non_mat
        and input("Delete non‑material unused assets? (yes/no): ").strip().lower()
        == "yes"
    ):
        freed = delete_paths(unused_non_mat)
        dirs_removed = clean_empty_dirs()
        for cat in ("sound", "particle", "image", "model"):
            print(f"{removed_non_mat[cat]} {cat} files deleted")
        print(
            f"{dirs_removed} empty directories removed, freed {humanize.naturalsize(freed)}"
        )
    entries, keep_dirs = extract_cdmaterials()
    unused_mat, removed_mat = find_unused_materials(
        lua_text, cats["material"], keep_dirs
    )
    size_mat = sum(os.path.getsize(p) for p in unused_mat)
    print(
        f"{len(unused_mat)} material assets totalling {humanize.naturalsize(size_mat)}"
    )
    if (
        unused_mat
        and input("Delete unused material assets? (yes/no): ").strip().lower() == "yes"
    ):
        freed = delete_paths(unused_mat)
        dirs_removed = clean_empty_dirs()
        print(f"{removed_mat} material files deleted")
        print(
            f"{dirs_removed} empty directories removed, freed {humanize.naturalsize(freed)}"
        )
    with open("cdmaterials.json", "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    print("cdmaterials.json saved")


if __name__ == "__main__":
    main()

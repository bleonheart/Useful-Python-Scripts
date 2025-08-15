import json
import logging
import os
import shutil
import sys
from collections import defaultdict
from pathlib import Path

from srctools.filesys import FileSystemChain, RawFileSystem, get_filesystem
from srctools.mdl import Model

ROOT = Path(r"C:\\Users\\David\\Desktop\\backup")
MERGE_SOURCE = Path(r"E:\\original")
GMOD_DIR = Path(r"D:\\SteamLibrary\\steamapps\\common\\GarrysMod\\garrysmod")
LUA_DIR = Path(
    r"E:\\GMOD\\Server\\garrysmod\\gamemodes\\metrorp\\devmodules\\bonemerge"
)
LOG_FILE = Path.home() / "Desktop" / "found_log.txt"
WORKSHOP_FILE = Path.home() / "Desktop" / "workshop_mdls.txt"
MATERIALS_FILE = Path.home() / "Desktop" / "materials_list.txt"
JSON_FILE = Path.home() / "Desktop" / "cdmaterials.json"
SOUND_EXTS = {".wav", ".mp3", ".ogg", ".flac", ".aac"}
PARTICLE_EXTS = {".pcf"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tga", ".dds", ".bmp", ".gif"}
MATERIAL_EXTS = {".vmt", ".vtf"}
MODEL_EXTS = {".mdl", ".phy", ".vvd", ".vtx", ".dx90.vtx"}
CORE_DIRS = {
    "lua",
    "materials",
    "models",
    "sound",
    "maps",
    "particles",
    "scripts",
    "resource",
    "cfg",
    "gamemodes",
    "shaders",
}
GB = 1024**3


def _n(p):
    return p.replace("\\", "/").lower()


def merge(s, d):
    for a in s.iterdir():
        if not a.is_dir():
            continue
        for f in a.rglob("*"):
            if not f.is_file():
                continue
            t = d / f.relative_to(a)
            t.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, t)


def flatten(r):
    for s in r.iterdir():
        if not s.is_dir() or s.name.lower() in CORE_DIRS:
            continue
        for f in s.rglob("*"):
            if not f.is_file():
                continue
            t = r / f.relative_to(s)
            t.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, t)


def read_lua():
    parts = []
    for p in LUA_DIR.rglob("*.lua"):
        try:
            parts.append(p.read_text("utf-8", "ignore"))
        except:
            pass
    return _n("\n".join(parts))


def gather():
    cats = defaultdict(list)
    me = sorted(MODEL_EXTS, key=lambda e: -len(e))
    for f in ROOT.rglob("*"):
        if not f.is_file():
            continue
        rel = _n(str(f.relative_to(ROOT)))
        n = f.name.lower()
        ext = next((e for e in me if n.endswith(e)), None)
        if ext:
            cats["model"].append((rel[: -len(ext)], f))
            continue
        ext = f.suffix.lower()
        if ext in SOUND_EXTS:
            cats["sound"].append((rel, f))
        elif ext in PARTICLE_EXTS:
            cats["particle"].append((rel, f))
        elif ext in IMAGE_EXTS:
            cats["image"].append((rel, f))
        elif ext in MATERIAL_EXTS:
            cats["material"].append((rel.rsplit(".", 1)[0], f))
    return cats


def extract_cdmaterials(fs, name):
    mdl = Model(fs, fs[name])
    return getattr(mdl, "cdmaterials", [])


def load_cdmaterials():
    entries = []
    keep = set()
    for base, _, files in os.walk(str(ROOT)):
        fs = FileSystemChain(RawFileSystem(base), get_filesystem(str(GMOD_DIR)))
        for fn in files:
            if not fn.lower().endswith(".mdl"):
                continue
            try:
                mats = extract_cdmaterials(fs, fn)
            except:
                mats = []
            entries.append({"model": str(Path(base) / fn), "materials": mats})
            for d in mats:
                nd = _n(os.path.join("materials", d.strip("/\\")) + "/")
                keep.add(nd)
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    return keep


def write_models(used):
    paths = [k + ".mdl" for k in used]
    WORKSHOP_FILE.write_text("\n".join(paths), encoding="utf-8")


def delete_unused_space(category, cats, used):
    freed = 0
    for k, f in cats[category]:
        if k not in used:
            try:
                freed += f.stat().st_size
                f.unlink()
            except:
                pass
    return freed


def write_materials(keep):
    paths = []
    for p in ROOT.rglob("materials/**/*"):
        if p.is_file():
            rel = _n(str(p.relative_to(ROOT)))
            if any(rel.startswith(k) for k in keep):
                paths.append(rel)
    MATERIALS_FILE.write_text("\n".join(paths), encoding="utf-8")
    return set(paths)


def delete_unused_materials(used):
    mats = [f for _, f in gather()["material"]]
    freed = 0
    for f in mats:
        rel = _n(str(f.relative_to(ROOT)))
        if rel not in used:
            try:
                freed += f.stat().st_size
                f.unlink()
            except:
                pass
    return freed


def clean_empty(root):
    for d in sorted(
        (p for p in root.rglob("*") if p.is_dir()), key=lambda p: -len(str(p))
    ):
        try:
            next(d.iterdir())
        except StopIteration:
            try:
                d.rmdir()
            except:
                pass


def main():
    logging.basicConfig(
        handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8")],
        level=logging.INFO,
        format="%(message)s",
    )
    merge(MERGE_SOURCE, ROOT)
    flatten(ROOT)
    lua = read_lua()
    cats = gather()
    before_models = sum(f.stat().st_size for _, f in cats["model"])
    used_models = {k for k, f in cats["model"] if k + ".mdl" in lua}
    write_models(used_models)
    freed_models = delete_unused_space("model", cats, used_models)
    after_models = before_models - freed_models
    before_sounds = sum(f.stat().st_size for _, f in cats["sound"])
    used_sounds = {k for k, f in cats["sound"] if k in lua}
    freed_sounds = delete_unused_space("sound", cats, used_sounds)
    after_sounds = before_sounds - freed_sounds
    before_particles = sum(f.stat().st_size for _, f in cats["particle"])
    used_particles = {k for k, f in cats["particle"] if k in lua}
    freed_particles = delete_unused_space("particle", cats, used_particles)
    after_particles = before_particles - freed_particles
    before_images = sum(f.stat().st_size for _, f in cats["image"])
    used_images = {k for k, f in cats["image"] if k in lua}
    freed_images = delete_unused_space("image", cats, used_images)
    after_images = before_images - freed_images
    keep = load_cdmaterials()
    before_materials = sum(f.stat().st_size for _, f in cats["material"])
    used_materials = write_materials(keep)
    freed_materials = delete_unused_materials(used_materials)
    after_materials = before_materials - freed_materials
    clean_empty(ROOT)
    print(
        f"Report:\n"
        f"Models: before {before_models/GB:.2f} GB, freed {freed_models/GB:.2f} GB, after {after_models/GB:.2f} GB\n"
        f"Sounds: before {before_sounds/GB:.2f} GB, freed {freed_sounds/GB:.2f} GB, after {after_sounds/GB:.2f} GB\n"
        f"Particles: before {before_particles/GB:.2f} GB, freed {freed_particles/GB:.2f} GB, after {after_particles/GB:.2f} GB\n"
        f"Images: before {before_images/GB:.2f} GB, freed {freed_images/GB:.2f} GB, after {after_images/GB:.2f} GB\n"
        f"Materials: before {before_materials/GB:.2f} GB, freed {freed_materials/GB:.2f} GB, after {after_materials/GB:.2f} GB"
    )


if __name__ == "__main__":
    main()

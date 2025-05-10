import os
import sys
import json
import shutil
import logging
from pathlib import Path
from collections import Counter
import humanize
from srctools.filesys import get_filesystem, RawFileSystem, FileSystemChain
from srctools.mdl import Model

DEFAULT_SOURCE = Path('C:/Users/Admin/AppData/Local/Temp/gmpublisher')
DEFAULT_DEST = Path('D:/Merged')
DEFAULT_LUA_LOCATION = DEFAULT_DEST
GMOD_DIR = Path('D:/SteamLibrary/steamapps/common/GarrysMod/garrysmod')

BAD_MODEL_FORMATS = ('.dx80.vtx', '.xbox.vtx', '.sw.vtx', '.360.vtx')
SOUND_EXTS = {'.wav', '.mp3', '.ogg', '.flac', '.aac'}
PARTICLE_EXTS = {'.pcf'}
IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.tga', '.dds', '.bmp', '.gif'}
MATERIAL_EXTS = {'.vmt', '.vtf'}
MODEL_EXTS = {'.mdl', '.phy', '.vvd', '.vtx', '.dx90.vtx'}

PACK_MAX_BYTES = int(1.9 * 1024**3)


def norm(path: str) -> str:
    return path.replace('\\', '/').lower()


def prompt_path(prompt: str, default: Path) -> Path:
    user = input(f'{prompt} [{default}]: ').strip()
    return Path(user) if user else default


def get_config():
    source = prompt_path('Source directory', DEFAULT_SOURCE)
    destination = prompt_path('Destination directory', DEFAULT_DEST)
    lua_location = prompt_path('Lua files location', DEFAULT_LUA_LOCATION)
    return source.resolve(), destination.resolve(), lua_location.resolve()


def merge_source_folders(source: Path, dest: Path):
    if not source.is_dir():
        logging.error('Source %s does not exist or is not a directory', source)
        sys.exit(1)
    dest.mkdir(parents=True, exist_ok=True)
    duplicates = 0
    space_saved = 0
    for sub in source.iterdir():
        if not sub.is_dir():
            continue
        for f in sub.rglob('*'):
            if not f.is_file():
                continue
            rel = f.relative_to(sub)
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                duplicates += 1
                space_saved += f.stat().st_size
                try:
                    f.unlink()
                except Exception as exc:
                    logging.warning('Failed to delete duplicate %s: %s', f, exc)
            else:
                try:
                    shutil.move(str(f), str(target))
                except Exception as exc:
                    logging.warning('Failed to move %s: %s', f, exc)
        try:
            shutil.rmtree(sub)
        except Exception as exc:
            logging.warning('Failed to remove folder %s: %s', sub, exc)
    return space_saved


def remove_redundant_formats(dest: Path):
    freed = 0
    for f in dest.rglob('*'):
        if not f.is_file():
            continue
        name = f.name.lower()
        for fmt in BAD_MODEL_FORMATS:
            if name.endswith(fmt):
                size = f.stat().st_size
                try:
                    f.unlink()
                    freed += size
                except Exception as exc:
                    logging.warning('Failed to remove %s: %s', f, exc)
                break
    return freed


def read_all_lua(root: Path) -> str:
    parts = []
    for base, _, files in os.walk(root):
        for fn in files:
            if fn.lower().endswith('.lua'):
                try:
                    with open(Path(base, fn), encoding='utf-8', errors='ignore') as fp:
                        parts.append(fp.read())
                except Exception:
                    pass
    return norm('\n'.join(parts))


def group_files(root: Path):
    cats = {c: {} for c in ('sound', 'particle', 'image', 'material', 'model')}
    model_exts = sorted(MODEL_EXTS, key=lambda e: -len(e))
    for base, _, files in os.walk(root):
        for fn in files:
            full = Path(base, fn)
            rel_norm = norm(str(full.relative_to(root)))
            lower = fn.lower()
            ext_match = next((e for e in model_exts if lower.endswith(e)), None)
            if ext_match:
                cat = 'model'
                key = rel_norm[:-len(ext_match)]
            else:
                ext = Path(lower).suffix
                if ext in SOUND_EXTS:
                    cat = 'sound'
                    key = rel_norm
                elif ext in PARTICLE_EXTS:
                    cat = 'particle'
                    key = rel_norm
                elif ext in IMAGE_EXTS:
                    cat = 'image'
                    key = rel_norm
                elif ext in MATERIAL_EXTS:
                    cat = 'material'
                    key = rel_norm[:-len(ext)]
                else:
                    continue
            cats[cat].setdefault(key, []).append(full)
    return cats


def find_unused_non_materials(lua_text: str, cats):
    unused = []
    sizes = Counter()
    for cat in ('sound', 'particle', 'image'):
        for key, paths in cats[cat].items():
            if key not in lua_text:
                for p in paths:
                    unused.append((p, cat))
                    sizes[cat] += p.stat().st_size
    for key, paths in cats['model'].items():
        if f'{key}.mdl' not in lua_text:
            for p in paths:
                unused.append((p, 'model'))
                sizes['model'] += p.stat().st_size
    return unused, sizes


def delete_paths(paths_with_cat):
    bytes_by_type = Counter()
    total = 0
    for p, cat in paths_with_cat:
        try:
            size = p.stat().st_size
            p.unlink()
            total += size
            bytes_by_type[cat] += size
        except Exception:
            pass
    return total, bytes_by_type


def clean_empty_dirs(root: Path):
    removed = 0
    for base, dirs, files in os.walk(root, topdown=False):
        if not dirs and not files:
            try:
                Path(base).rmdir()
                removed += 1
            except OSError:
                pass
    return removed


def extract_cdmaterials(root: Path):
    entries = []
    keep_dirs = set()
    fs = FileSystemChain(RawFileSystem(root), get_filesystem(GMOD_DIR))
    for mdl in root.rglob('*.mdl'):
        rel = mdl.relative_to(root)
        try:
            cdirs = Model(fs, fs[str(rel)]).cdmaterials
        except Exception:
            cdirs = []
        mats = []
        for d in cdirs:
            nd = norm(Path('materials', d.strip('/\\')).as_posix() + '/')
            keep_dirs.add(nd)
            mats.append(nd)
        entries.append({'model': str(mdl), 'materials': mats})
    return entries, keep_dirs


def find_unused_materials(lua_text: str, mats: dict, keep_dirs: set, root: Path):
    unused = []
    for _, paths in mats.items():
        for p in paths:
            rel_norm = norm(str(p.relative_to(root)))
            key = norm(str(p.with_suffix('')))
            if not any(rel_norm.startswith(d) for d in keep_dirs) and key + '.vmt' not in lua_text and key + '.vtf' not in lua_text:
                unused.append(p)
    return unused


def lua_cleanup(root: Path):
    lua_text = read_all_lua(root)
    cats = group_files(root)
    unused_non_mat, sizes_non_mat = find_unused_non_materials(lua_text, cats)
    print(f'Unused non-material assets: {len(unused_non_mat)} ({humanize.naturalsize(sum(sizes_non_mat.values()))})')
    freed_non_mat = 0
    freed_by_type = Counter()
    if unused_non_mat and input('Delete unused non-material assets? (yes/no): ').strip().lower() == 'yes':
        freed_non_mat, freed_by_type = delete_paths(unused_non_mat)
        clean_empty_dirs(root)
        print(f'Freed {humanize.naturalsize(freed_non_mat)} by removing non-material assets')
    entries, keep_dirs = extract_cdmaterials(root)
    with open('cdmaterials.json', 'w', encoding='utf-8') as fp:
        json.dump(entries, fp, ensure_ascii=False, indent=2)
    mats_unused = find_unused_materials(lua_text, cats['material'], keep_dirs, root)
    print(f'Unused materials: {len(mats_unused)} ({humanize.naturalsize(sum(p.stat().st_size for p in mats_unused))})')
    freed_mat = 0
    if mats_unused and input('Delete unused material assets? (yes/no): ').strip().lower() == 'yes':
        paths_with_cat = [(p, 'material') for p in mats_unused]
        freed_mat, mat_bytes = delete_paths(paths_with_cat)
        freed_by_type.update(mat_bytes)
        clean_empty_dirs(root)
        print(f'Freed {humanize.naturalsize(freed_mat)} by removing materials')
    return freed_non_mat, freed_mat, freed_by_type


def split_into_packs(dest: Path, max_bytes: int):
    pack = 1
    current = 0
    for f in sorted(dest.rglob('*')):
        if not f.is_file():
            continue
        if f.relative_to(dest).parts[0].isdigit():
            continue
        size = f.stat().st_size
        if current + size > max_bytes:
            pack += 1
            current = 0
        target = dest / str(pack) / f.relative_to(dest).parent
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(f), str(target / f.name))
        current += size
    logging.info('Splitting complete')


def summarize(merge_bytes, format_bytes, freed_non_mat, freed_mat, freed_by_type):
    total_unused = freed_non_mat + freed_mat
    total_saved = merge_bytes + format_bytes + total_unused
    print('\nSpace Savings Report')
    print('--------------------')
    print(f'From merging duplicate files: {humanize.naturalsize(merge_bytes)}')
    print(f'From deleting redundant formats: {humanize.naturalsize(format_bytes)}')
    print(f'From deleting unused assets (total): {humanize.naturalsize(total_unused)}')
    print('Breakdown by type:')
    for t in ('sound', 'image', 'material', 'model', 'particle'):
        print(f'  {t.capitalize()}: {humanize.naturalsize(freed_by_type.get(t, 0))}')
    print(f'Total general space saved: {humanize.naturalsize(total_saved)}')


def main():
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    source, dest, _ = get_config()
    logging.info('Merging source folders...')
    merge_bytes = merge_source_folders(source, dest)
    logging.info('Removing redundant model formats...')
    format_bytes = remove_redundant_formats(dest)
    logging.info('Lua-aware cleanup...')
    freed_non_mat, freed_mat, freed_by_type = lua_cleanup(dest)
    logging.info('Splitting files into packs...')
    split_into_packs(dest, PACK_MAX_BYTES)
    summarize(merge_bytes, format_bytes, freed_non_mat, freed_mat, freed_by_type)
    try:
        Path('cdmaterials.json').unlink()
    except FileNotFoundError:
        pass


if __name__ == '__main__':
    main()

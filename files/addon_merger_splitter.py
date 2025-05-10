import shutil
import sys
import logging
from pathlib import Path

def get_paths():
    default_source = Path("C:/Users/Admin/AppData/Local/Temp/gmpublisher")
    default_destination = Path("D:/Merged")
    user_source = input(f"Enter the SOURCE path or press Enter to use [{default_source}]: ").strip()
    if user_source:
        default_source = Path(user_source)
    user_destination = input(f"Enter the DESTINATION path or press Enter to use [{default_destination}]: ").strip()
    if user_destination:
        default_destination = Path(user_destination)
    return default_source, default_destination

def merge_folders(source: Path, destination: Path):
    if not source.is_dir():
        logging.error("Source path %s does not exist or is not a directory", source)
        sys.exit(1)
    destination.mkdir(parents=True, exist_ok=True)
    files_moved = 0
    duplicates = 0
    space_saved = 0
    for folder in source.iterdir():
        if not folder.is_dir():
            continue
        logging.info("Processing folder: %s", folder)
        for file in folder.rglob("*"):
            if not file.is_file():
                continue
            relative = file.relative_to(folder)
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                duplicates += 1
                space_saved += file.stat().st_size
                try:
                    file.unlink()
                except Exception as e:
                    logging.warning("Failed to remove duplicate %s: %s", file, e)
            else:
                try:
                    shutil.move(str(file), str(target))
                    files_moved += 1
                except Exception as e:
                    logging.warning("Failed to move %s: %s", file, e)
        try:
            shutil.rmtree(folder)
        except Exception as e:
            logging.warning("Failed to remove folder %s: %s", folder, e)
        logging.info("Removed folder: %s", folder)
    logging.info("Merge Operation Summary:")
    logging.info("Files moved: %d", files_moved)
    logging.info("Duplicates found: %d", duplicates)
    logging.info("Space saved from duplicates: %.2f KB", space_saved / 1024)

def clean_formats(destination: Path):
    bad_formats = [".dx80.vtx", ".xbox.vtx", ".sw.vtx", ".360.vtx"]
    removed_count = 0
    removed_size = 0
    removed_per_format = {fmt: 0 for fmt in bad_formats}
    for file in destination.rglob("*"):
        if not file.is_file():
            continue
        name_lower = file.name.lower()
        for fmt in bad_formats:
            if name_lower.endswith(fmt):
                size = file.stat().st_size
                try:
                    file.unlink()
                except Exception as e:
                    logging.warning("Failed to remove %s: %s", file, e)
                else:
                    removed_count += 1
                    removed_size += size
                    removed_per_format[fmt] += 1
                break
    logging.info("Unused files removed: %d, Space freed: %.2f KB", removed_count, removed_size / 1024)
    logging.info("Breakdown per format:")
    for fmt, count in removed_per_format.items():
        logging.info("%s removed: %d", fmt, count)

def split_into_packs(destination: Path, max_pack_size_bytes: int):
    current_pack = 1
    current_size = 0
    all_files = [f for f in destination.rglob("*") if f.is_file()]
    for file in all_files:
        size = file.stat().st_size
        if current_size + size > max_pack_size_bytes:
            current_pack += 1
            current_size = 0
        relative = file.relative_to(destination)
        pack_folder = destination / str(current_pack) / relative.parent
        pack_folder.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(str(file), str(pack_folder / file.name))
            current_size += size
        except Exception as e:
            logging.warning("Failed to copy %s to pack %d: %s", file, current_pack, e)
    logging.info("Splitting complete. Packs have been created under %s", destination)

def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    source, destination = get_paths()
    logging.info("")
    logging.info("Starting Merge Operation...")
    logging.info("Source: %s", source)
    logging.info("Destination: %s", destination)
    merge_folders(source, destination)
    logging.info("")
    logging.info("Removing unused model formats...")
    clean_formats(destination)
    logging.info("")
    logging.info("Starting Split Operation on: %s", destination)
    max_pack_size_bytes = int(1.9 * 1024**3)
    split_into_packs(destination, max_pack_size_bytes)

if __name__ == "__main__":
    main()

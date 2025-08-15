import logging
import shutil
import sys
from pathlib import Path

DEFAULT_SOURCE_PATH = Path(r"C:\Users\David\Desktop\backup")
DEFAULT_DESTINATION_PATH = Path(r"C:\Users\David\Desktop\Merged")
DEFAULT_MAX_PACK_SIZE = int(1.9 * 1024**3)


def get_paths():
    source_default = DEFAULT_SOURCE_PATH
    destination_default = DEFAULT_DESTINATION_PATH
    src_input = input(
        f"Enter the SOURCE path or press Enter to use [{source_default}]: "
    ).strip()
    dst_input = input(
        f"Enter the DESTINATION path or press Enter to use [{destination_default}]: "
    ).strip()
    source = Path(src_input) if src_input else source_default
    destination = Path(dst_input) if dst_input else destination_default
    return source, destination


def merge_folders(source: Path, destination: Path):
    if not source.is_dir():
        logging.error("Source path %s does not exist or is not a directory", source)
        sys.exit(1)
    destination.mkdir(parents=True, exist_ok=True)
    files_copied = 0
    duplicates = 0
    space_saved = 0
    for folder in source.iterdir():
        if not folder.is_dir():
            continue
        for file in folder.rglob("*"):
            if not file.is_file():
                continue
            rel = file.relative_to(folder)
            target = destination / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            size = file.stat().st_size
            if target.exists():
                duplicates += 1
                space_saved += size
            else:
                try:
                    shutil.copy2(file, target)
                    files_copied += 1
                except Exception as e:
                    logging.warning("Failed to copy %s: %s", file, e)
    logging.info("Merge Operation Summary:")
    logging.info("Files copied: %d", files_copied)
    logging.info("Duplicates skipped: %d", duplicates)
    logging.info("Potential space saved: %.2f KB", space_saved / 1024)


def split_into_packs(destination: Path, max_pack_size: int):
    pack_index = 1
    current_size = 0
    all_files = [f for f in destination.rglob("*") if f.is_file()]
    for file in all_files:
        size = file.stat().st_size
        if current_size + size > max_pack_size:
            pack_index += 1
            current_size = 0
        rel = file.relative_to(destination)
        pack_dir = destination / str(pack_index) / rel.parent
        pack_dir.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(file, pack_dir / file.name)
            current_size += size
        except Exception as e:
            logging.warning("Failed to copy %s to pack %d: %s", file, pack_index, e)
    logging.info("Splitting complete. Packs created under %s", destination)


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    source, destination = get_paths()
    logging.info("Starting merge from %s to %s", source, destination)
    merge_folders(source, destination)
    logging.info("Starting split into packs")
    split_into_packs(destination, DEFAULT_MAX_PACK_SIZE)


if __name__ == "__main__":
    main()

from pathlib import Path

root_dir = Path(r"E:\GMOD\Server\garrysmod\gamemodes\falloutrp\schema\aid")
for file_path in root_dir.rglob("sh_*.lua"):
    target = file_path.with_name(file_path.name[3:])
    try:
        file_path.rename(target)
        print(f"Renamed {file_path} -> {target}")
    except Exception as e:
        print(f"Failed to rename {file_path}: {e}")

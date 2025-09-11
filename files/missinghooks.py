import sys
import re
from pathlib import Path
from datetime import datetime

DEFAULT_GAMEMODE_ROOT = Path(r"E:\\GMOD\\Server\\garrysmod\\gamemodes\\Lilia\\gamemode")
DEFAULT_DOC_MD = Path(r"E:\\GMOD\\Server\\garrysmod\\gamemodes\\Lilia\\documentation\\docs\\hooks\\gamemode_hooks.md")

root = DEFAULT_GAMEMODE_ROOT
doc_path = DEFAULT_DOC_MD

module_pat = re.compile(r"^\s*function\s+MODULE\s*[:.]\s*([A-Za-z_]\w*)\s*\(", re.MULTILINE)
gm_pat = re.compile(r"^\s*function\s+GM\s*[:.]\s*([A-Za-z_]\w*)\s*\(", re.MULTILINE)
schema_pat = re.compile(r"^\s*function\s+SCHEMA\s*[:.]\s*([A-Za-z_]\w*)\s*\(", re.MULTILINE)
hook_add_pat = re.compile(r'hook\s*\.\s*Add\s*\(\s*([\'"])([^\'"]+)\1')
hook_run_pat = re.compile(r'hook\s*\.\s*Run\s*\(\s*([\'"])([^\'"]+)\1')
doc_hook_pat = re.compile(r"^\s*###\s+`?([A-Za-z_][\w:]*)`?\s*$", re.MULTILINE)

def scan_hooks(root_path):
    names = set()
    for p in root_path.rglob("*.lua"):
        try:
            s = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        names.update(module_pat.findall(s))
        names.update(gm_pat.findall(s))
        names.update(schema_pat.findall(s))
        names.update(t[1] for t in hook_add_pat.findall(s))
        names.update(t[1] for t in hook_run_pat.findall(s))
    return set(sorted(names, key=str.lower))

def read_documented_hooks(path):
    try:
        doc = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return set()
    return set(doc_hook_pat.findall(doc))

def unique_output_path(base_dir, base_name, ext):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    p = base_dir / f"{base_name}_{ts}{ext}"
    if not p.exists():
        return p
    i = 1
    while True:
        q = base_dir / f"{base_name}_{ts}_{i}{ext}"
        if not q.exists():
            return q
        i += 1

def write_new_file(lines, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = unique_output_path(out_dir, "hooks_missing_from_docs", ".txt")
    try:
        with out_path.open("x", encoding="utf-8") as f:
            f.write("\n".join(sorted(lines, key=str.lower)))
            if lines:
                f.write("\n")
        return True
    except Exception:
        return False

def main():
    hooks = scan_hooks(root)
    documented = read_documented_hooks(doc_path)
    missing = [h for h in hooks if h not in documented]
    out_dir = doc_path.parent
    ok = write_new_file(missing, out_dir)
    if not ok:
        sys.exit(1)

if __name__ == "__main__":
    main()

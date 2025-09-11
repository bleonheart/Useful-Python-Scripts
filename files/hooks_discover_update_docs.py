import re
import sys
from pathlib import Path

DEFAULT_GAMEMODE_ROOT = Path(r"E:\\GMOD\\Server\\garrysmod\\gamemodes\\Lilia\\gamemode")
DEFAULT_DOC_MD = Path(
    r"E:\\GMOD\\Server\\garrysmod\\gamemodes\\Lilia\\documentation\\docs\\hooks\\gamemode_hooks.md"
)

root = DEFAULT_GAMEMODE_ROOT
doc_path = DEFAULT_DOC_MD
hooks_out_path = root / "unique_hooks.txt"
missing_out_path = doc_path.parent / "hooks_missing_from_docs.txt"

module_pat = re.compile(
    r"^\s*function\s+MODULE\s*[:.]\s*([A-Za-z_]\w*)\s*\(", re.MULTILINE
)
gm_pat = re.compile(r"^\s*function\s+GM\s*[:.]\s*([A-Za-z_]\w*)\s*\(", re.MULTILINE)
schema_pat = re.compile(
    r"^\s*function\s+SCHEMA\s*[:.]\s*([A-Za-z_]\w*)\s*\(", re.MULTILINE
)
hook_add_pat = re.compile(r'hook\s*\.\s*Add\s*\(\s*([\'"])([^\'"]+)\1')
hook_run_pat = re.compile(r'hook\s*\.\s*Run\s*\(\s*([\'"])([^\'"]+)\1')
doc_hook_pat = re.compile(r"^\s*###\s+`?([A-Za-z_][\w:]*)`?\s*$", re.MULTILINE)
marker_pat = re.compile(r"^\s*###\s+XXXXXXXXXXXX\s*$", re.MULTILINE)


def prompt_bool(msg, default=False):
    s = input(f"{msg} [{'Y/n' if default else 'y/N'}]: ").strip().lower()
    if not s:
        return default
    return s in ("y", "yes")


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
        return "", set()
    return doc, set(doc_hook_pat.findall(doc))


def write_hooks_file(hooks, path):
    try:
        path.write_text("\n".join(hooks) + ("\n" if hooks else ""), encoding="utf-8")
        return True
    except Exception as e:
        print(f"Failed to write hooks file: {e}")
        return False


def write_missing_file(missing, path):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "\n".join(sorted(missing, key=str.lower)) + ("\n" if missing else ""),
            encoding="utf-8",
        )
        return True
    except Exception as e:
        print(f"Failed to write missing comparison: {e}")
        return False


def update_docs_file(doc, documented, missing, path):
    if not missing:
        print("No new hooks to register in documentation.")
        return False
    sections = "\n".join(f"### {h}\n" for h in missing) + "\n"
    if marker_pat.search(doc):
        new_doc = marker_pat.sub(sections.rstrip("\n"), doc, count=1)
    else:
        sep = "\n\n" if doc.strip() else ""
        new_doc = doc.rstrip() + sep + sections
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        backup_path = path.with_suffix(path.suffix + ".bak")
        backup_path.write_text(doc, encoding="utf-8")
        path.write_text(new_doc, encoding="utf-8")
        return True
    except Exception as e:
        print(f"Failed to update documentation: {e}")
        return False


def main():
    hooks = scan_hooks(root)
    print(f"Discovered {len(hooks)} hooks.")
    if prompt_bool(f"Write unique hooks list to {hooks_out_path}?", True):
        ok = write_hooks_file(hooks, hooks_out_path)
        if not ok:
            sys.exit(1)
        print(f"Wrote {len(hooks)} hooks to {hooks_out_path}.")
    doc, documented = read_documented_hooks(doc_path)
    print(f"Documentation has {len(documented)} registered hooks.")
    missing = [h for h in hooks if h not in documented]
    print(f"{len(missing)} hooks missing from documentation.")
    if prompt_bool(f"Create comparison file at {missing_out_path}?", True):
        ok = write_missing_file(missing, missing_out_path)
        if not ok:
            sys.exit(1)
        print(f"Wrote missing comparison to {missing_out_path}.")
    if prompt_bool(f"Register missing hooks into {doc_path}?", True):
        ok = update_docs_file(doc, documented, missing, doc_path)
        if not ok:
            sys.exit(1)
        print(f"Documentation updated at {doc_path}.")


if __name__ == "__main__":
    main()
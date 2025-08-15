import json
import os
import re
from datetime import datetime

REPO_ROOT = "E:/GMOD/Server/garrysmod/gamemodes/Lilia"
GAMEMODE_DIR = os.path.join(REPO_ROOT, "gamemode")
LANG_FILE = os.path.join(GAMEMODE_DIR, "languages", "english.lua")
DATA_DIR = os.path.join(REPO_ROOT, "data")
REGISTERED_JSON_PATH = os.path.join(DATA_DIR, "lilia_registered_privileges.json")
REPORT_MD_PATH = os.path.join(REPO_ROOT, "lilia_privilege_report.md")
MODULES_DIR = r"E:\GMOD\Server\garrysmod\gamemodes\metrorp\gitmodules"


def extract_used_privileges_in_dir(base_dir: str) -> list[str]:
    pattern = re.compile(
        r"[:.]hasPrivilege\s*\(\s*(['\"])([^'\"\s)]+)\1\s*\)", re.IGNORECASE | re.DOTALL
    )
    privileges: set[str] = set()
    for root, _, files in os.walk(base_dir):
        for fname in files:
            if not fname.lower().endswith(".lua"):
                continue
            path = os.path.join(root, fname)
            try:
                with open(path, encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
                for _, pid in pattern.findall(content):
                    privileges.add(pid)
            except OSError:
                continue
    return sorted(privileges)


def extract_used_privileges() -> list[str]:
    return extract_used_privileges_in_dir(GAMEMODE_DIR)


def load_localizations() -> dict[str, str]:
    localizations: dict[str, str] = {}
    try:
        with open(LANG_FILE, encoding="utf-8", errors="ignore") as fh:
            content = fh.read()
        for k, v in re.findall(r'^\s*(\w+)\s*=\s*"(.*?)"\s*$', content, re.MULTILINE):
            localizations[k] = v
        for k, v in re.findall(
            r'^\s*L\.\s*(\w+)\s*=\s*"(.*?)"\s*$', content, re.MULTILINE
        ):
            localizations[k] = v
        for k, v in re.findall(
            r'L\[\s*["\']([^"\']+)["\']\s*\]\s*=\s*["\']([^"\']*)["\']',
            content,
            re.MULTILINE,
        ):
            localizations[k] = v
        for k, v in re.findall(
            r'lia\.(?:lang|language)\.Add\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']*)["\']\s*\)',
            content,
            re.IGNORECASE,
        ):
            localizations[k] = v
    except OSError:
        pass
    return localizations


def load_registered_raw():
    try:
        with open(REGISTERED_JSON_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def extract_registered_ids_from_json(x) -> list[str]:
    if x is None:
        return []
    ids: list[str] = []
    seen: set[str] = set()

    def add(v):
        s = str(v)
        if s and s != "None" and s not in seen:
            seen.add(s)
            ids.append(s)

    def walk(v):
        if isinstance(v, list):
            for i in v:
                walk(i)
        elif isinstance(v, dict):
            for k, val in v.items():
                if k.lower() == "id" and isinstance(val, (str, int)):
                    add(val)
                elif k.lower() == "privileges":
                    walk(val)
                elif isinstance(val, (list, dict)):
                    walk(val)
        elif isinstance(v, (str, int)):
            add(v)

    walk(x)
    return sorted(ids)


def extract_ids_from_privileges_blocks(content: str) -> list[str]:
    ids: set[str] = set()
    start_pos = 0
    while True:
        m = re.search(r"\bPrivileges\s*=\s*\{", content[start_pos:], re.IGNORECASE)
        if not m:
            break
        block_start = start_pos + m.end() - 1
        i = block_start
        depth = 0
        in_str = False
        str_ch = ""
        escape = False
        while i < len(content):
            ch = content[i]
            if in_str:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == str_ch:
                    in_str = False
            else:
                if ch in ('"', "'"):
                    in_str = True
                    str_ch = ch
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        block_end = i
                        break
            i += 1
        else:
            block_end = len(content)
        block = content[block_start : block_end + 1]
        for pid in re.findall(r'(?i)\bID\s*=\s*["\']([^"\']+)["\']', block):
            ids.add(pid)
        start_pos = block_end + 1
    return sorted(ids)


def extract_registered_ids_from_lua_dir(base_dir: str) -> list[str]:
    ids: set[str] = set()
    for root, _, files in os.walk(base_dir):
        for fname in files:
            if not fname.lower().endswith(".lua"):
                continue
            path = os.path.join(root, fname)
            try:
                with open(path, encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
                for pid in extract_ids_from_privileges_blocks(content):
                    ids.add(pid)
            except OSError:
                continue
    return sorted(ids)


def extract_registered_ids_from_lua() -> list[str]:
    return extract_registered_ids_from_lua_dir(GAMEMODE_DIR)


def build_framework_report(
    used: list[str], registered: list[str], localizations: dict[str, str]
) -> dict:
    used_set = set(used)
    registered_set = set(registered)
    missing = sorted(used_set - registered_set)
    unused = sorted(registered_set - used_set)
    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "repo_root": REPO_ROOT,
        "counts": {
            "used_in_code": len(used),
            "registered": len(registered),
            "used_but_not_registered": len(missing),
            "registered_but_not_used": len(unused),
        },
        "used_but_not_registered": [
            {"id": p, "name": localizations.get(p, "")} for p in missing
        ],
        "registered_but_not_used": [
            {"id": p, "name": localizations.get(p, "")} for p in unused
        ],
    }


def escape_md(s: str) -> str:
    return s.replace("|", r"\|").replace("<", r"\<").replace(">", r"\>")


def discover_modules(modules_root: str) -> list[tuple[str, str]]:
    modules: list[tuple[str, str]] = []
    try:
        for entry in os.scandir(modules_root):
            if not entry.is_dir():
                continue
            has_lua = False
            for r, _, fs in os.walk(entry.path):
                if any(f.lower().endswith(".lua") for f in fs):
                    has_lua = True
                    break
            if has_lua:
                modules.append((entry.name, entry.path))
    except OSError:
        pass
    modules.sort(key=lambda x: x[0].lower())
    return modules


def build_module_reports(
    modules_root: str, framework_registered: list[str], localizations: dict[str, str]
) -> list[dict]:
    reports: list[dict] = []
    modules = discover_modules(modules_root)
    fr_set = set(framework_registered)
    for name, path in modules:
        used = extract_used_privileges_in_dir(path)
        reg_ids = extract_registered_ids_from_lua_dir(path)
        allowed = fr_set | set(reg_ids)
        missing = sorted(set(used) - allowed)
        reports.append(
            {
                "name": name,
                "path": path,
                "counts": {
                    "used_in_code": len(used),
                    "registered_in_module": len(reg_ids),
                    "missing_registrations": len(missing),
                },
                "used_but_not_registered": [
                    {"id": p, "name": localizations.get(p, "")} for p in missing
                ],
            }
        )
    return reports


def write_markdown_report(
    framework: dict, modules: list[dict], modules_root: str, path: str
) -> None:
    lines: list[str] = []
    lines.append("# Lilia Privilege Report")
    lines.append("")
    lines.append(f"- Generated at: `{framework['generated_at']}`")
    lines.append(f"- Framework repo root: `{framework['repo_root']}`")
    lines.append(f"- Modules root: `{modules_root}`")
    lines.append("")
    lines.append("## Framework")
    c = framework["counts"]
    lines.append(f"- Used in code: **{c['used_in_code']}**")
    lines.append(f"- Registered: **{c['registered']}**")
    lines.append(f"- Used but not registered: **{c['used_but_not_registered']}**")
    lines.append(f"- Registered but not used: **{c['registered_but_not_used']}**")
    lines.append("")
    lines.append("### Used but not registered")
    if c["used_but_not_registered"] == 0:
        lines.append("_None_")
    else:
        lines.append("| ID | Name |")
        lines.append("|---|---|")
        for item in framework["used_but_not_registered"]:
            pid = escape_md(item["id"])
            name = escape_md(item["name"] or "")
            lines.append(f"| `{pid}` | {name} |")
    lines.append("")
    lines.append("### Registered but not used")
    if c["registered_but_not_used"] == 0:
        lines.append("_None_")
    else:
        lines.append("| ID | Name |")
        lines.append("|---|---|")
        for item in framework["registered_but_not_used"]:
            pid = escape_md(item["id"])
            name = escape_md(item["name"] or "")
            lines.append(f"| `{pid}` | {name} |")
    lines.append("")
    lines.append("## Modules")
    if not modules:
        lines.append("_No modules found_")
    else:
        for m in modules:
            lines.append(f"### {escape_md(m['name'])}")
            mc = m["counts"]
            lines.append(f"- Used in code: **{mc['used_in_code']}**")
            lines.append(f"- Registered in module: **{mc['registered_in_module']}**")
            lines.append(f"- Missing registrations: **{mc['missing_registrations']}**")
            lines.append("")
            lines.append("#### Used but not registered")
            if mc["missing_registrations"] == 0:
                lines.append("_None_")
            else:
                lines.append("| ID | Name |")
                lines.append("|---|---|")
                for item in m["used_but_not_registered"]:
                    pid = escape_md(item["id"])
                    name = escape_md(item["name"] or "")
                    lines.append(f"| `{pid}` | {name} |")
            lines.append("")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    os.replace(tmp_path, path)


def main() -> None:
    used = extract_used_privileges()
    loc = load_localizations()
    reg_raw = load_registered_raw()
    reg_ids_json = extract_registered_ids_from_json(reg_raw)
    reg_ids_lua = extract_registered_ids_from_lua()
    reg_ids = sorted(set(reg_ids_json) | set(reg_ids_lua))
    framework = build_framework_report(used, reg_ids, loc)
    modules = build_module_reports(MODULES_DIR, reg_ids, loc)
    write_markdown_report(framework, modules, MODULES_DIR, REPORT_MD_PATH)
    print(f"Markdown: {REPORT_MD_PATH}")


if __name__ == "__main__":
    main()

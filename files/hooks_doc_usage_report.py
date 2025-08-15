import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

DOC_FILE = r"E:\GMOD\Server\garrysmod\gamemodes\Lilia\documentation\docs\hooks\gamemode_hooks.md"
CODE_ROOT = r"E:\GMOD\Server\garrysmod\gamemodes\Lilia\gamemode"
OUTPUT_REPORT = r"E:\GMOD\Server\garrysmod\gamemodes\Lilia\hook_report.md"

DOC_HEADING_RE = re.compile(r"^\s*###\s+([A-Za-z_][A-Za-z0-9_]*)\b")

HOOK_RUN_RE = re.compile(r"hook\.Run\s*\(\s*([\"'])([^\"']+)\1")

HOOK_CALL_RE = re.compile(r"hook\.Call\s*\(\s*([\"'])([^\"']+)\1")

HOOK_ADD_RE = re.compile(r"hook\.Add\s*\(\s*([\"'])([^\"']+)\1")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def read_lines(path: Path) -> List[str]:
    return read_text(path).splitlines()


def collect_documented_hooks(doc_path: Path) -> Set[str]:
    hooks: Set[str] = set()
    for line in read_lines(doc_path):
        m = DOC_HEADING_RE.match(line)
        if m:
            hooks.add(m.group(1))
    return hooks


def walk_lua_files(root: Path) -> List[Path]:
    return [p for p in root.rglob("*.lua") if p.is_file()]


def collect_matches(rx: re.Pattern, text: str) -> List[str]:
    return [m.group(2) for m in rx.finditer(text)]


def collect_used_hooks(
    root: Path,
) -> Tuple[Set[str], Dict[str, List[Tuple[Path, int]]]]:
    hooks: Set[str] = set()
    locations: Dict[str, List[Tuple[Path, int]]] = {}
    for lua in walk_lua_files(root):
        lines = read_lines(lua)
        for idx, line in enumerate(lines, start=1):
            for rx in (HOOK_RUN_RE, HOOK_CALL_RE):
                m = rx.search(line)
                if m:
                    name = m.group(2)
                    hooks.add(name)
                    locations.setdefault(name, []).append((lua, idx))
    return hooks, locations


def collect_consumed_hooks(
    root: Path,
) -> Tuple[Set[str], Dict[str, List[Tuple[Path, int]]]]:
    hooks: Set[str] = set()
    locations: Dict[str, List[Tuple[Path, int]]] = {}
    for lua in walk_lua_files(root):
        lines = read_lines(lua)
        for idx, line in enumerate(lines, start=1):
            m = HOOK_ADD_RE.search(line)
            if m:
                name = m.group(2)
                hooks.add(name)
                locations.setdefault(name, []).append((lua, idx))
    return hooks, locations


def rel(p: Path, base: Path) -> str:
    try:
        return str(p.relative_to(base))
    except Exception:
        return str(p)


def write_report(
    doc_file: Path,
    code_root: Path,
    out_file: Path,
    documented: Set[str],
    used: Set[str],
    used_locs: Dict[str, List[Tuple[Path, int]]],
    consumed: Set[str],
    consumed_locs: Dict[str, List[Tuple[Path, int]]],
) -> None:
    used_and_documented = sorted(used & documented)
    used_not_documented = sorted(used - documented)
    documented_not_used = sorted(documented - used)

    consumed_not_used = sorted((consumed - used))

    lines: List[str] = []
    lines.append("# Gamemode Hooks Usage vs Documentation\n")
    lines.append(f"- Documentation: `{doc_file}`")
    lines.append(f"- Scanned code: `{code_root}`")
    lines.append("")
    lines.append("## Summary\n")
    lines.append(f"- Documented hooks: {len(documented)}")
    lines.append(f"- Used hooks (hook.Run/Call): {len(used)}")
    lines.append(f"- Registered listeners (hook.Add): {len(consumed)}")
    lines.append(f"- Used but NOT documented: {len(used_not_documented)}")
    lines.append(f"- Documented but NOT used: {len(documented_not_used)}")
    lines.append("")

    def emit_with_locations(
        title: str, names: List[str], locs: Dict[str, List[Tuple[Path, int]]]
    ):
        lines.append(f"### {title} ({len(names)})\n")
        if not names:
            lines.append("_None_\n")
            return
        for name in names:
            lines.append(f"- `{name}`")
            for p, ln in (locs.get(name) or [])[:8]:
                lines.append(f"  - {rel(p, code_root)}:{ln}")
        lines.append("")

    def emit_list(title: str, names: List[str]):
        lines.append(f"### {title} ({len(names)})\n")
        if not names:
            lines.append("_None_\n")
            return
        chunk: List[str] = []
        for n in names:
            chunk.append(f"`{n}`")
            if len(chunk) == 10:
                lines.append("- " + ", ".join(chunk))
                chunk = []
        if chunk:
            lines.append("- " + ", ".join(chunk))
        lines.append("")

    emit_with_locations("Used and documented", used_and_documented, used_locs)
    emit_with_locations("Used but NOT documented", used_not_documented, used_locs)
    emit_list("Documented but NOT used (stale?)", documented_not_used)
    emit_with_locations(
        "Listeners present but never fired (hook.Add only)",
        consumed_not_used,
        consumed_locs,
    )

    out_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote report to: {out_file}")


def main():
    doc_file = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(DOC_FILE)
    code_root = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(CODE_ROOT)
    out_file = Path(sys.argv[3]) if len(sys.argv) > 3 else Path(OUTPUT_REPORT)

    if not doc_file.is_file():
        print(f"Documentation file not found: {doc_file}", file=sys.stderr)
        sys.exit(1)
    if not code_root.is_dir():
        print(f"Code root not found: {code_root}", file=sys.stderr)
        sys.exit(1)

    documented = collect_documented_hooks(doc_file)
    used, used_locs = collect_used_hooks(code_root)
    consumed, consumed_locs = collect_consumed_hooks(code_root)

    write_report(
        doc_file=doc_file,
        code_root=code_root,
        out_file=out_file,
        documented=documented,
        used=used,
        used_locs=used_locs,
        consumed=consumed,
        consumed_locs=consumed_locs,
    )


if __name__ == "__main__":
    main()

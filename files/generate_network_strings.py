import re
import sys
from pathlib import Path

DEFAULT_LUA_ROOT = Path(r"E:\GMOD\Server\garrysmod\gamemodes\Lilia\gamemode")
DEFAULT_OUTPUT_LUA = Path("networking.lua")
DEFAULT_MODULE_ROOTS = [
    Path(r"E:\GMOD\Server\garrysmod\gamemodes\metrorp\modules"),
    Path(r"E:\GMOD\Server\garrysmod\gamemodes\metrorp\gitmodules"),
    Path(r"E:\GMOD\Server\garrysmod\gamemodes\metrorp\devmodules"),
]

PATTERNS = [
    re.compile(r"net\.Start\(\s*['\"]([^'\"]+)['\"]"),
    re.compile(r"net\.Receive\(\s*['\"]([^'\"]+)['\"]"),
    re.compile(r"util\.AddNetworkString\(\s*['\"]([^'\"]+)['\"]"),
    re.compile(r"lia\.net\.readBigTable\(\s*['\"]([^'\"]+)['\"]"),
    re.compile(r"lia\.net\.writeBigTable\([^,]*,\s*['\"]([^'\"]+)['\"]"),
]

NETWORK_TABLE_RE = re.compile(r"MODULE\.NetworkStrings\s*=\s*\{.*?\}", re.DOTALL)


def find_net_messages(root: Path) -> set[str]:
    messages = set()
    for path in root.rglob("*.lua"):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeError):
            continue
        for pattern in PATTERNS:
            for m in pattern.finditer(text):
                messages.add(m.group(1))
    return messages


def escape_lua_string(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def write_lua_file(messages: list[str], output_path: Path) -> bool:
    if not messages:
        return False
    esc = [escape_lua_string(m) for m in messages]
    body = "".join(f'    "{s}",\n' for s in esc[:-1]) + f'    "{esc[-1]}"\n'
    lua = "local networkStrings = {\n" + body + "}\n"
    lua += "for _, netString in ipairs(networkStrings) do\n    util.AddNetworkString(netString)\nend\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(lua, encoding="utf-8")
    return True


def build_module_block(messages: list[str]) -> str:
    if not messages:
        return ""
    esc = [escape_lua_string(m) for m in messages]
    body = "".join(f'        "{s}",\n' for s in esc[:-1]) + f'        "{esc[-1]}"\n'
    return "MODULE.NetworkStrings ={\n" + body + "}\n\n"


def update_module_lua(module_dir: Path, messages: list[str]) -> bool:
    module_path = module_dir / "module.lua"
    if not module_path.is_file() or not messages:
        return False
    try:
        text = module_path.read_text(encoding="utf-8", errors="ignore")
    except (OSError, UnicodeError):
        return False
    block = build_module_block(messages)
    if not block:
        return False
    if NETWORK_TABLE_RE.search(text):
        new_text = NETWORK_TABLE_RE.sub(block.strip(), text)
    else:
        new_text = block + text
    try:
        module_path.write_text(new_text, encoding="utf-8")
    except OSError:
        return False
    return True


def generate_module_files(module_roots: list[Path]) -> None:
    for root in module_roots:
        if not root.is_dir():
            continue
        for module_dir in [p for p in root.iterdir() if p.is_dir()]:
            messages = sorted(find_net_messages(module_dir))
            updated = update_module_lua(module_dir, messages)
            if updated:
                print(f"Inserted MODULE.NetworkStrings at top of '{module_dir / 'module.lua'}'")
            elif write_lua_file(messages, module_dir / DEFAULT_OUTPUT_LUA.name):
                print(f"Wrote {len(messages)} network strings to '{module_dir / DEFAULT_OUTPUT_LUA.name}'")
            else:
                print(f"Skipped '{module_dir}': no network strings found")


def main() -> None:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_LUA_ROOT
    output = Path(sys.argv[2]) if len(sys.argv) > 2 else root / DEFAULT_OUTPUT_LUA.name
    if not root.is_dir():
        print(f"Error: '{root}' is not a valid directory", file=sys.stderr)
        sys.exit(1)
    messages = sorted(find_net_messages(root))
    if write_lua_file(messages, output):
        print(f"Wrote {len(messages)} network strings to '{output}'")
    else:
        print("No network strings found; not creating a Lua file")
    generate_module_files(DEFAULT_MODULE_ROOTS)


if __name__ == "__main__":
    main()
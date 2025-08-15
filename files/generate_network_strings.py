import re
import sys
from pathlib import Path

DEFAULT_LUA_ROOT = Path(r"E:\GMOD\Server\garrysmod\gamemodes\Lilia\gamemode")
DEFAULT_OUTPUT_LUA = Path("network_strings.lua")

PATTERNS = [
    re.compile(r"net\.Start\(\s*['\"]([^'\"]+)['\"]"),
    re.compile(r"net\.Receive\(\s*['\"]([^'\"]+)['\"]"),
    re.compile(r"util\.AddNetworkString\(\s*['\"]([^'\"]+)['\"]"),
    re.compile(r"lia\.net\.readBigTable\(\s*['\"]([^'\"]+)['\"]"),
    re.compile(r"lia\.net\.writeBigTable\([^,]*,\s*['\"]([^'\"]+)['\"]"),
]

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

def write_lua_file(messages: list[str], output_path: Path) -> None:
    esc = [m.replace("\\", "\\\\").replace('"', '\\"') for m in messages]
    body = "".join(f'    "{s}",\n' for s in esc[:-1])
    if esc:
        body += f'    "{esc[-1]}"\n'
    lua = "local networkStrings = {\n" + body + "}\n"
    lua += "for _, netString in ipairs(networkStrings) do\n    util.AddNetworkString(netString)\nend\n"
    output_path.write_text(lua, encoding="utf-8")

def main() -> None:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_LUA_ROOT
    output = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUTPUT_LUA
    if not root.is_dir():
        print(f"Error: '{root}' is not a valid directory", file=sys.stderr)
        sys.exit(1)
    messages = sorted(find_net_messages(root))
    write_lua_file(messages, output)
    print(f"Wrote {len(messages)} network strings to '{output}'")

if __name__ == "__main__":
    main()

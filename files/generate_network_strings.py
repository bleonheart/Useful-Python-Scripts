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

NETWORK_TABLE_RE = re.compile(r"^\s*MODULE\.NetworkStrings\s*=\s*\{.*?\}\s*\n?", re.DOTALL | re.MULTILINE)


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
    try:
        output_path.write_text(lua, encoding="utf-8")
    except OSError:
        return False
    return True


def build_module_block(messages: list[str]) -> str:
    if not messages:
        return ""
    esc = [escape_lua_string(m) for m in messages]
    body = "".join(f'        "{s}",\n' for s in esc[:-1]) + f'        "{esc[-1]}"\n'
    return "MODULE.NetworkStrings = {\n" + body + "}\n\n"


def update_module_lua(module_dir: Path, messages: list[str]) -> bool:
    module_path = module_dir / "module.lua"
    if not module_path.is_file():
        return False
    try:
        text = module_path.read_text(encoding="utf-8", errors="ignore")
    except (OSError, UnicodeError):
        return False
    text_no_block = NETWORK_TABLE_RE.sub("", text)
    if not messages:
        if text_no_block != text:
            try:
                module_path.write_text(text_no_block, encoding="utf-8")
            except OSError:
                return False
            return True
        return False
    block = build_module_block(messages)
    if not block:
        return False
    new_text = block + text_no_block.lstrip()
    try:
        module_path.write_text(new_text, encoding="utf-8")
    except OSError:
        return False
    return True


def iter_module_dirs(root: Path):
    seen = set()
    for mod_file in root.rglob("module.lua"):
        parent = mod_file.parent.resolve()
        if parent not in seen:
            seen.add(parent)
            yield parent


def generate_module_files(module_roots: list[Path]) -> None:
    for root in module_roots:
        if not root.is_dir():
            print(f"Skipped '{root}': not a directory")
            continue
        for module_dir in iter_module_dirs(root):
            messages = sorted(find_net_messages(module_dir))
            updated = update_module_lua(module_dir, messages)
            if updated and messages:
                print(f"Replaced MODULE.NetworkStrings in '{module_dir / 'module.lua'}'")
            elif updated:
                print(f"Removed MODULE.NetworkStrings (no messages) in '{module_dir / 'module.lua'}'")
            elif write_lua_file(messages, module_dir / DEFAULT_OUTPUT_LUA.name):
                print(f"Wrote {len(messages)} network strings to '{module_dir / DEFAULT_OUTPUT_LUA.name}'")
            else:
                print(f"Skipped '{module_dir}': no network strings found")


def prompt_yes_no(msg: str, default: bool | None = None) -> bool:
    suffix = " [y/n]: " if default is None else (" [Y/n]: " if default else " [y/N]: ")
    while True:
        try:
            resp = input(msg + suffix).strip().lower()
        except EOFError:
            return bool(default)
        if not resp and default is not None:
            return default
        if resp in ("y", "yes"):
            return True
        if resp in ("n", "no"):
            return False
        print("Please answer y or n.")


def main() -> None:
    args = sys.argv[1:]
    if len(args) >= 1:
        root = Path(args[0])
    else:
        root = DEFAULT_LUA_ROOT
    if len(args) >= 2:
        output = Path(args[1])
    else:
        output = root / DEFAULT_OUTPUT_LUA.name
    proceed_root = prompt_yes_no(f"Do you want to run it in '{root}'?", True)
    if proceed_root:
        if not root.is_dir():
            print(f"Error: '{root}' is not a valid directory", file=sys.stderr)
        else:
            messages = sorted(find_net_messages(root))
            if write_lua_file(messages, output):
                print(f"Wrote {len(messages)} network strings to '{output}'")
            else:
                print("No network strings found; not creating a Lua file")
    module_roots = []
    for p in DEFAULT_MODULE_ROOTS:
        if prompt_yes_no(f"Do you want to run it in '{p}'?", True):
            module_roots.append(p)
    if module_roots:
        generate_module_files(module_roots)
    else:
        print("No module roots selected")


if __name__ == "__main__":
    main()
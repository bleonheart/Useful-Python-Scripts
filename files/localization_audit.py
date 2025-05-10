import re
import json
from pathlib import Path

LOC_FILE = Path(r"E:\Server\garrysmod\gamemodes\Lilia\gamemode\languages\english.lua")
ROOTS = [
    Path(r"E:\Server\garrysmod\gamemodes\Lilia"),
    Path(r"E:\Server\garrysmod\gamemodes\metrorp\modules")
]

def extract_defined_keys(path):
    text = path.read_text(encoding='utf-8')
    return {m.group(1) for m in re.finditer(r'(\w+)\s*=\s*"[^"]*"', text)}

def extract_placeholders(path):
    text = path.read_text(encoding='utf-8')
    return {m.group(1): m.group(2) for m in re.finditer(r'(\w+)\s*=\s*"([^"]*%(?:\d+\$)?[sd][^"]*)"', text)}

def count_placeholders(template):
    return len(re.findall(r'%(?:\d+\$)?[sd]', template))

def parse_args(fragment):
    args, cur = [], ''
    depth = in_quote = esc = 0
    quote = ''
    for ch in fragment:
        if esc:
            cur += ch
            esc = 0
        elif ch == '\\':
            cur += ch
            esc = 1
        elif in_quote:
            cur += ch
            if ch == quote:
                in_quote = 0
        elif ch in ('"', "'"):
            cur += ch
            in_quote = 1
            quote = ch
        elif ch == '(':
            cur += ch
            depth += 1
        elif ch == ')':
            depth -= 1
            cur += ch
        elif ch == ',' and depth == 0:
            args.append(cur.strip())
            cur = ''
        else:
            cur += ch
    if cur.strip():
        args.append(cur.strip())
    return args

def scan_localization_usage(roots):
    patterns = {
        'L': re.compile(r'(?<![\w:.])L\('),
        'notifyLocalized': re.compile(r'(?<![\w:.])notifyLocalized\(')
    }
    usage = {'L': {}, 'notifyLocalized': {}}
    for root in roots:
        for file in root.rglob('*.lua'):
            lines = file.read_text(encoding='utf-8').splitlines()
            for lineno, line in enumerate(lines, 1):
                for func, pat in patterns.items():
                    for match in pat.finditer(line):
                        i = match.end()
                        depth = 1
                        in_quote = esc = 0
                        quote = ''
                        fragment = ''
                        while i < len(line) and depth:
                            ch = line[i]
                            fragment += ch
                            if esc:
                                esc = 0
                            elif ch == '\\':
                                esc = 1
                            elif in_quote:
                                if ch == quote:
                                    in_quote = 0
                            elif ch in ('"', "'"):
                                in_quote = 1
                                quote = ch
                            elif ch == '(':
                                depth += 1
                            elif ch == ')':
                                depth -= 1
                            i += 1
                        parts = parse_args(fragment[:-1])
                        if not parts:
                            continue
                        raw = parts[0].strip()
                        if len(raw) < 2 or raw[0] not in ('"', "'") or raw[-1] != raw[0]:
                            continue
                        key = raw[1:-1]
                        provided = len(parts) - 1
                        usage[func].setdefault(key, []).append((f'{file}:{lineno}', provided))
    return usage

def main():
    defined = extract_defined_keys(LOC_FILE)
    placeholders = extract_placeholders(LOC_FILE)
    usage = scan_localization_usage(ROOTS)
    missing_l = sorted(k for k in usage['L'] if k not in defined)
    missing_n = sorted(k for k in usage['notifyLocalized'] if k not in defined)
    total_l = sum(len(v) for v in usage['L'].values())
    total_n = sum(len(v) for v in usage['notifyLocalized'].values())
    mismatches = {}
    for func, entries in usage.items():
        for key, occ in entries.items():
            expected = count_placeholders(placeholders.get(key, ''))
            for loc, got in occ:
                if got != expected:
                    mismatches.setdefault(func, {}).setdefault(key, {'expected': expected, 'found': []})['found'].append({'location': loc, 'provided': got})
    print(f"Found {len(defined)} defined entries in {LOC_FILE}")
    print(f"Found {len(placeholders)} placeholder entries")
    for k, v in placeholders.items():
        print(f"{k}: {v}")
    print(f"\nFound {total_l} L(...) usages across {len(usage['L'])} keys")
    for k, v in usage['L'].items():
        print(f'L("{k}"): {len(v)} occurrences')
    print(f"\nFound {total_n} notifyLocalized(...) usages across {len(usage['notifyLocalized'])} keys")
    for k, v in usage['notifyLocalized'].items():
        print(f'notifyLocalized("{k}"): {len(v)} occurrences')
    if missing_l:
        print("\nKeys used in L(...) but not defined:")
        for key in missing_l:
            print(f"  {key}")
    if missing_n:
        print("\nKeys used in notifyLocalized(...) but not defined:")
        for key in missing_n:
            print(f"  {key}")
    if mismatches:
        print("\nArgument mismatches:")
        for func, keys in mismatches.items():
            for key, info in keys.items():
                print(f'{func}("{key}") expected {info["expected"]} args')
                for e in info['found']:
                    print(f'  {e["location"]}: provided {e["provided"]}')
    desk = Path.home() / "Desktop"
    (desk / "argloc.json").write_text(json.dumps(placeholders, ensure_ascii=False, indent=2), encoding='utf-8')
    (desk / "loc_usage.json").write_text(json.dumps(usage, ensure_ascii=False, indent=2), encoding='utf-8')
    (desk / "loc_missing.json").write_text(json.dumps({'L_missing': missing_l, 'notifyLocalized_missing': missing_n}, ensure_ascii=False, indent=2), encoding='utf-8')
    (desk / "loc_mismatch.json").write_text(json.dumps(mismatches, ensure_ascii=False, indent=2), encoding='utf-8')

if __name__ == "__main__":
    main()
import argparse
import datetime
import os
import re
import shutil
import sys

DEFAULT_FRAMEWORK_GAMEMODE_DIR = r"E:\GMOD\Server\garrysmod\gamemodes\Lilia\gamemode"
DEFAULT_FRAMEWORK_LANGUAGES_DIR = (
    r"E:\GMOD\Server\garrysmod\gamemodes\Lilia\gamemode\languages"
)
DEFAULT_MODULES_ROOT = r"E:\GMOD\Server\garrysmod\gamemodes\metrorp\gitmodules"
DEFAULT_MODULES_DIR = r"E:\GMOD\Server\garrysmod\gamemodes\metrorp\modules"
DEFAULT_DEVMODULES_DIR = r"E:\GMOD\Server\garrysmod\gamemodes\metrorp\devmodules"
DEFAULT_OUT_PATTERN = "localization_report_{name}.md"
DEFAULT_LIMIT = 500


def unquote(v):
    if not v:
        return v
    if v[0] == v[-1] and v[0] in ("'", '"'):
        return v[1:-1]
    m = re.match(r"^\[=*\[(.*)\]=*\]$", v, re.S)
    return m.group(1) if m else v


def extract_block(s, start, open_ch, close_ch):
    i = start
    n = len(s)
    depth = 0
    in_str = None
    long_eq = None
    in_line_comment = False
    in_block_comment = False
    block_eq = None
    start_body = None
    while i < n:
        ch = s[i]
        nxt = s[i + 1] if i + 1 < n else ""
        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue
        if in_block_comment:
            if ch == "]" and block_eq is not None:
                k = i + 1
                eqs = 0
                while k < n and s[k] == "=":
                    eqs += 1
                    k += 1
                if k < n and s[k] == "]" and eqs == block_eq:
                    in_block_comment = False
                    i = k + 1
                    continue
            i += 1
            continue
        if in_str:
            if in_str in ("'", '"'):
                if ch == "\\":
                    i += 2
                    continue
                if ch == in_str:
                    in_str = None
                i += 1
                continue
            if in_str == "[":
                if ch == "]" and long_eq is not None:
                    k = i + 1
                    eqs = 0
                    while k < n and s[k] == "=":
                        eqs += 1
                        k += 1
                    if k < n and s[k] == "]" and eqs == long_eq:
                        in_str = None
                        i = k + 1
                        continue
                i += 1
                continue
        else:
            if ch == "-" and nxt == "-":
                if i + 2 < n and s[i + 2] == "[":
                    k = i + 3
                    eqs = 0
                    while k < n and s[k] == "=":
                        eqs += 1
                        k += 1
                    if k < n and s[k] == "[":
                        in_block_comment = True
                        block_eq = eqs
                        i = k + 1
                        continue
                in_line_comment = True
                i += 2
                continue
            if ch in ("'", '"'):
                in_str = ch
                i += 1
                continue
            if ch == "[":
                k = i + 1
                eqs = 0
                while k < n and s[k] == "=":
                    eqs += 1
                    k += 1
                if k < n and s[k] == "[":
                    in_str = "["
                    long_eq = eqs
                    i = k + 1
                    continue
        if (
            ch == open_ch
            and not in_str
            and not in_line_comment
            and not in_block_comment
        ):
            depth += 1
            if depth == 1:
                start_body = i + 1
        elif (
            ch == close_ch
            and not in_str
            and not in_line_comment
            and not in_block_comment
        ):
            depth -= 1
            if depth == 0:
                return s[start_body:i], i
        i += 1
    return None, None


def load_language_keys(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        src = f.read()
    keys = []
    seen = set()
    r_dot = re.compile(
        r'\bLANGUAGE\.(\w+)\s*=\s*("([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\'|\[=*\[.*?\]=*\])',
        re.S,
    )
    r_idx = re.compile(
        r'\bLANGUAGE\[\s*(["\'])(.*?)\1\s*\]\s*=\s*("([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\'|\[=*\[.*?\]=*\])',
        re.S,
    )
    for m in r_dot.finditer(src):
        k = m.group(1)
        if k not in seen:
            seen.add(k)
            keys.append(k)
    for m in r_idx.finditer(src):
        k = m.group(2)
        if k not in seen:
            seen.add(k)
            keys.append(k)
    r_tbl_start = re.compile(r"\bLANGUAGE\s*=\s*\{", re.S)
    pos = 0
    while True:
        m = r_tbl_start.search(src, pos)
        if not m:
            break
        body, endpos = extract_block(src, src.find("{", m.start()), "{", "}")
        if body is None:
            pos = m.end()
            continue
        r_tbl1 = re.compile(
            r'(\w+)\s*=\s*("([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\'|\[=*\[.*?\]=*\])', re.S
        )
        r_tbl2 = re.compile(
            r'\[\s*(["\'])(.*?)\1\s*\]\s*=\s*("([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\'|\[=*\[.*?\]=*\])',
            re.S,
        )
        for t in r_tbl1.finditer(body):
            k = t.group(1)
            if k not in seen:
                seen.add(k)
                keys.append(k)
        for t in r_tbl2.finditer(body):
            k = t.group(2)
            if k not in seen:
                seen.add(k)
                keys.append(k)
        pos = endpos + 1
    return keys


def load_language_map(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        src = f.read()
    mp = {}
    r_dot = re.compile(
        r'\bLANGUAGE\.(\w+)\s*=\s*("([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\'|\[=*\[.*?\]=*\])',
        re.S,
    )
    r_idx = re.compile(
        r'\bLANGUAGE\[\s*(["\'])(.*?)\1\s*\]\s*=\s*("([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\'|\[=*\[.*?\]=*\])',
        re.S,
    )
    for m in r_dot.finditer(src):
        mp[m.group(1)] = unquote(m.group(2))
    for m in r_idx.finditer(src):
        mp[m.group(2)] = unquote(m.group(3))
    r_tbl_start = re.compile(r"\bLANGUAGE\s*=\s*\{", re.S)
    pos = 0
    while True:
        m = r_tbl_start.search(src, pos)
        if not m:
            break
        body, endpos = extract_block(src, src.find("{", m.start()), "{", "}")
        if body is None:
            pos = m.end()
            continue
        r_tbl1 = re.compile(
            r'(\w+)\s*=\s*(("([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\'|\[=*\[.*?\]=*\]))', re.S
        )
        r_tbl2 = re.compile(
            r'\[\s*(["\'])(.*?)\1\s*(=\s*(("([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\'|\[=*\[.*?\]=*\]))|\s*,)',
            re.S,
        )
        for t in r_tbl1.finditer(body):
            mp[t.group(1)] = unquote(t.group(2))
        for t in r_tbl2.finditer(body):
            if "=" in t.group(0):
                mp[t.group(2)] = unquote(t.group(4))
        pos = endpos + 1
    return mp


def build_line_starts(s):
    a = [0]
    for i, ch in enumerate(s):
        if ch == "\n":
            a.append(i + 1)
    return a


def pos_to_line_col(starts, pos):
    import bisect

    i = bisect.bisect_right(starts, pos) - 1
    return i + 1, pos - starts[i] + 1


def iter_string_literals(src):
    n = len(src)
    i = 0
    in_line_comment = False
    in_block_comment = False
    block_eq = None
    in_str = None
    long_eq = None
    while i < n:
        ch = src[i]
        nxt = src[i + 1] if i + 1 < n else ""
        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue
        if in_block_comment:
            if ch == "]" and block_eq is not None:
                k = i + 1
                eqs = 0
                while k < n and src[k] == "=":
                    eqs += 1
                    k += 1
                if k < n and src[k] == "]" and eqs == block_eq:
                    in_block_comment = False
                    i = k + 1
                    continue
            i += 1
            continue
        if in_str:
            if in_str in ("'", '"'):
                if ch == "\\":
                    i += 2
                    continue
                if ch == in_str:
                    yield (src[str_start + 1 : i], str_start)
                    in_str = None
                i += 1
                continue
            if in_str == "[":
                if ch == "]":
                    k = i + 1
                    eqs = 0
                    while k < n and src[k] == "=":
                        eqs += 1
                        k += 1
                    if k < n and src[k] == "]" and eqs == long_eq:
                        yield (src[str_start_content:i], str_start)
                        in_str = None
                        i = k + 1
                        continue
                i += 1
                continue
        else:
            if ch == "-" and nxt == "-":
                if i + 2 < n and src[i + 2] == "[":
                    k = i + 3
                    eqs = 0
                    while k < n and src[k] == "=":
                        eqs += 1
                        k += 1
                    if k < n and src[k] == "[":
                        in_block_comment = True
                        block_eq = eqs
                        i = k + 1
                        continue
                in_line_comment = True
                i += 2
                continue
            if ch in ("'", '"'):
                in_str = ch
                str_start = i
                i += 1
                continue
            if ch == "[":
                k = i + 1
                eqs = 0
                while k < n and src[k] == "=":
                    eqs += 1
                    k += 1
                if k < n and src[k] == "[":
                    in_str = "["
                    long_eq = eqs
                    str_start = i
                    str_start_content = k + 1
                    i = k + 1
                    continue
        i += 1


def split_top_level(s):
    res = []
    n = len(s)
    i = 0
    start = 0
    in_line_comment = False
    in_block_comment = False
    block_eq = None
    in_str = None
    long_eq = None
    stk = []
    while i < n:
        ch = s[i]
        nxt = s[i + 1] if i + 1 < n else ""
        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue
        if in_block_comment:
            if ch == "]" and block_eq is not None:
                k = i + 1
                eqs = 0
                while k < n and s[k] == "=":
                    eqs += 1
                    k += 1
                if k < n and s[k] == "]" and eqs == block_eq:
                    in_block_comment = False
                    i = k + 1
                    continue
            i += 1
            continue
        if in_str:
            if in_str in ("'", '"'):
                if ch == "\\":
                    i += 2
                    continue
                if ch == in_str:
                    in_str = None
                i += 1
                continue
            if in_str == "[":
                if ch == "]":
                    k = i + 1
                    eqs = 0
                    while k < n and s[k] == "=":
                        eqs += 1
                        k += 1
                    if k < n and s[k] == "]" and eqs == long_eq:
                        in_str = None
                        i = k + 1
                        continue
                i += 1
                continue
        else:
            if ch == "-" and nxt == "-":
                if i + 2 < n and s[i + 2] == "[":
                    k = i + 3
                    eqs = 0
                    while k < n and s[k] == "=":
                        eqs += 1
                        k += 1
                    if k < n and s[k] == "[":
                        in_block_comment = True
                        block_eq = eqs
                        i = k + 1
                        continue
                in_line_comment = True
                i += 2
                continue
            if ch in ("'", '"'):
                in_str = ch
                i += 1
                continue
            if ch == "[":
                k = i + 1
                eqs = 0
                while k < n and s[k] == "=":
                    eqs += 1
                    k += 1
                if k < n and s[k] == "[":
                    in_str = "["
                    long_eq = eqs
                    i = k + 1
                    continue
            if ch in "([{":
                stk.append(ch)
                i += 1
                continue
            if ch in ")]}":
                if stk:
                    stk.pop()
                i += 1
                continue
            if ch == "," and not stk:
                res.append(s[start:i].strip())
                i += 1
                start = i
                continue
        i += 1
    tail = s[start:].strip()
    if tail != "":
        res.append(tail)
    return res


def count_placeholders(fmt):
    if not fmt:
        return 0
    return len(
        re.findall(
            r"%(?!%)(?:\d+\$)?[+\- #0]*?(?:\d+|\*)?(?:\.(?:\d+|\*))?(?:[hlL]?)[cdiouxXeEfgGqsa]",
            fmt,
        )
    )


def iter_localization_calls(src):
    n = len(src)
    i = 0
    in_line_comment = False
    in_block_comment = False
    block_eq = None
    in_str = None
    long_eq = None
    while i < n:
        ch = src[i]
        nxt = src[i + 1] if i + 1 < n else ""
        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue
        if in_block_comment:
            if ch == "]" and block_eq is not None:
                k = i + 1
                eqs = 0
                while k < n and src[k] == "=":
                    eqs += 1
                    k += 1
                if k < n and src[k] == "]" and eqs == block_eq:
                    in_block_comment = False
                    i = k + 1
                    continue
            i += 1
            continue
        else:
            if ch == "-" and nxt == "-":
                if i + 2 < n and src[i + 2] == "[":
                    k = i + 3
                    eqs = 0
                    while k < n and src[k] == "=":
                        eqs += 1
                        k += 1
                    if k < n and src[k] == "[":
                        in_block_comment = True
                        block_eq = eqs
                        i = k + 1
                        continue
                in_line_comment = True
                i += 2
                continue
            if ch == "_" or ch.isalpha():
                j = i + 1
                while j < n and (src[j] == "_" or src[j].isalnum()):
                    j += 1
                name = src[i:j]
                prev = src[i - 1] if i - 1 >= 0 else ""
                if name in ("notifyLocalized", "L"):
                    kind = None
                    if prev == ":":
                        kind = f"method:{name}"
                    elif name == "L":
                        before = src[i - 1] if i - 1 >= 0 else ""
                        if not (before == "." or (before == "_" or before.isalnum())):
                            kind = "func:L"
                    if kind:
                        k = j
                        while k < n and src[k].isspace():
                            k += 1
                        if k < n and src[k] == "(":
                            body, endpos = extract_block(src, k, "(", ")")
                            if body is not None:
                                m = re.match(
                                    r'^\s*("([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\'|\[=*\[.*?\]=*\])',
                                    body,
                                    re.S,
                                )
                                if m:
                                    lit = m.group(1)
                                    key = unquote(lit)
                                    args = split_top_level(body)
                                    num_extra = max(0, len(args) - 1)
                                    yield (key, num_extra, kind, i)
                                i = endpos + 1
                                continue
                if name == "Run" and prev == ".":
                    p = i - 2
                    while p >= 0 and src[p].isspace():
                        p -= 1
                    q = p
                    while q >= 0 and (src[q] == "_" or src[q].isalnum()):
                        q -= 1
                    callee = src[q + 1 : p + 1]
                    if callee == "hook":
                        k = j
                        while k < n and src[k].isspace():
                            k += 1
                        if k < n and src[k] == "(":
                            body, endpos = extract_block(src, k, "(", ")")
                            if body is not None:
                                args = split_top_level(body)
                                if args:
                                    m = re.match(
                                        r'^\s*("([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\'|\[=*\[.*?\]=*\])\s*$',
                                        args[0],
                                    )
                                    if m:
                                        hook_name = unquote(m.group(1))

                                        def yield_if_literal(expr, kindname, posi):
                                            mm = re.match(
                                                r'^\s*("([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\'|\[=*\[.*?\]=*\])\s*$',
                                                expr,
                                            )
                                            if mm:
                                                yield_key = unquote(mm.group(1))
                                                yield (yield_key, 0, kindname, posi)

                                        if hook_name in (
                                            "AddSection",
                                            "AddTextField",
                                            "AddBarField",
                                        ):
                                            kindname = f"hook:{hook_name}"
                                            if len(args) >= 2:
                                                for tup in yield_if_literal(
                                                    args[1], kindname, i
                                                ):
                                                    yield tup
                                            if (
                                                hook_name
                                                in ("AddTextField", "AddBarField")
                                                and len(args) >= 4
                                            ):
                                                for tup in yield_if_literal(
                                                    args[3], kindname, i
                                                ):
                                                    yield tup
                                i = endpos + 1
                                continue
                if name in ("AddSection", "AddTextField", "AddBarField"):
                    kind = "method:" + name if prev == ":" else "func:" + name
                    k = j
                    while k < n and src[k].isspace():
                        k += 1
                    if k < n and src[k] == "(":
                        body, endpos = extract_block(src, k, "(", ")")
                        if body is not None:
                            args = split_top_level(body)

                            def yield_if_literal(expr):
                                mm = re.match(
                                    r'^\s*("([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\'|\[=*\[.*?\]=*\])\s*$',
                                    expr,
                                )
                                return unquote(mm.group(1)) if mm else None

                            if args:
                                if len(args) >= 1:
                                    k1 = yield_if_literal(args[0])
                                    if k1 is not None:
                                        yield (k1, 0, kind, i)
                                if (
                                    name in ("AddTextField", "AddBarField")
                                    and len(args) >= 3
                                ):
                                    k2 = yield_if_literal(args[2])
                                    if k2 is not None:
                                        yield (k2, 0, kind, i)
                            i = endpos + 1
                            continue
                if name == "add" and prev == ".":
                    p1 = i - 2
                    while p1 >= 0 and src[p1].isspace():
                        p1 -= 1
                    q1 = p1
                    while q1 >= 0 and (src[q1] == "_" or src[q1].isalnum()):
                        q1 -= 1
                    ident2 = src[q1 + 1 : p1 + 1]
                    if ident2 == "keybind":
                        if q1 >= 0 and src[q1] == ".":
                            p0 = q1 - 1
                            while p0 >= 0 and src[p0].isspace():
                                p0 -= 1
                            q0 = p0
                            while q0 >= 0 and (src[q0] == "_" or src[q0].isalnum()):
                                q0 -= 1
                            ident1 = src[q0 + 1 : p0 + 1]
                            if ident1 == "lia":
                                k = j
                                while k < n and src[k].isspace():
                                    k += 1
                                if k < n and src[k] == "(":
                                    body, endpos = extract_block(src, k, "(", ")")
                                    if body is not None:
                                        args = split_top_level(body)
                                        if len(args) >= 2:
                                            mm = re.match(
                                                r'^\s*("([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\'|\[=*\[.*?\]=*\])\s*$',
                                                args[1],
                                            )
                                            if mm:
                                                key = unquote(mm.group(1))
                                                yield (
                                                    key,
                                                    0,
                                                    "call:lia.keybind.add",
                                                    i,
                                                )
                                        i = endpos + 1
                                        continue
                i = j
                continue
            if ch in ("'", '"'):
                in_str = ch
                i += 1
                continue
            if ch == "[":
                k = i + 1
                eqs = 0
                while k < n and src[k] == "=":
                    eqs += 1
                    k += 1
                if k < n and src[k] == "[":
                    in_str = "["
                    long_eq = eqs
                    i = k + 1
                    continue
        i += 1


def relpath(p, base):
    try:
        return os.path.relpath(p, base).replace("\\", "/")
    except ValueError:
        return p.replace("\\", "/")


def scan_usages(scan_dir, language_file, keys):
    used = {k: [] for k in keys}
    for root, _, files in os.walk(scan_dir):
        for name in files:
            if not name.lower().endswith(".lua"):
                continue
            path = os.path.join(root, name)
            if os.path.abspath(path) == os.path.abspath(language_file):
                continue
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                src = f.read()
            starts = build_line_starts(src)
            for lit, pos in iter_string_literals(src):
                if lit in used:
                    line, col = pos_to_line_col(starts, pos)
                    used[lit].append((path, line, col))
    return used


def scan_localization_calls(scan_dir, language_file, keys, placeholders):
    undefined = []
    mismatches = []
    keyset = set(keys)
    all_used_keys = set()
    for root, _, files in os.walk(scan_dir):
        for name in files:
            if not name.lower().endswith(".lua"):
                continue
            path = os.path.join(root, name)
            if os.path.abspath(path) == os.path.abspath(language_file):
                continue
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                src = f.read()
            starts = build_line_starts(src)
            for key, num_extra, kind, pos in iter_localization_calls(src):
                all_used_keys.add(key)
                line, col = pos_to_line_col(starts, pos)
                if key not in keyset:
                    undefined.append((path, line, col, key, kind))
                else:
                    exp = placeholders.get(key, 0)
                    if num_extra != exp:
                        mismatches.append((path, line, col, key, exp, num_extra, kind))
    return undefined, mismatches, all_used_keys


def write_header(f, cols):
    f.write("\t".join(cols) + "\n")


def md_escape(s):
    return str(s).replace("|", r"\|" )


def md_code(s):
    return f"`{md_escape(s)}`"


def write_markdown_table(f, headers, rows):
    f.write("| " + " | ".join(headers) + " |\n")
    f.write("|" + "|".join(["---"] * len(headers)) + "|\n")
    for r in rows:
        f.write("| " + " | ".join(str(x) for x in r) + " |\n")
    f.write("\n")


def analyze_data(language_file, scan_dir):
    keys = load_language_keys(language_file)
    lang_map = load_language_map(language_file)
    placeholders = {k: count_placeholders(v) for k, v in lang_map.items()}
    used_map = scan_usages(scan_dir, language_file, keys)
    total_hits = sum(len(v) for v in used_map.values())
    unused = sorted(k for k, hits in used_map.items() if not hits)
    undefined, mismatches, all_used_keys = scan_localization_calls(
        scan_dir, language_file, keys, placeholders
    )
    undefined_rows = [
        (relpath(pth, scan_dir), ln, col, kind, key)
        for pth, ln, col, key, kind in undefined
    ]
    undefined_rows.sort(key=lambda r: (r[0].lower(), r[1], r[2], r[3], r[4].lower()))
    mismatch_rows = [
        (relpath(pth, scan_dir), ln, col, kind, key, exp, got)
        for pth, ln, col, key, exp, got, kind in mismatches
    ]
    mismatch_rows.sort(key=lambda r: (r[0].lower(), r[1], r[2], r[3], r[4].lower()))
    defined_keys_set = set(keys)
    undefined_key_names = sorted(all_used_keys - defined_keys_set)
    files_with_undef = {r[0] for r in undefined_rows}
    files_with_mismatch = {r[0] for r in mismatch_rows}
    return {
        "language_file": language_file,
        "scan_dir": scan_dir,
        "keys": keys,
        "lang_map": lang_map,
        "total_hits": total_hits,
        "unused": unused,
        "undefined_rows": undefined_rows,
        "mismatch_rows": mismatch_rows,
        "undefined_key_names": undefined_key_names,
        "files_with_undef": files_with_undef,
        "files_with_mismatch": files_with_mismatch,
    }


def write_framework_md(f, data, limit):
    write_markdown_table(
        f,
        ["Language file", "Framework dir"],
        [[md_code(data["language_file"]), md_code(data["scan_dir"])]],
    )
    write_markdown_table(
        f,
        ["Metric", "Value"],
        [
            ["Unique keys", len(data["keys"])],
            ["Total key usages found", data["total_hits"]],
        ],
    )
    write_markdown_table(
        f,
        ["Metric", "Value"],
        [
            ["Unused keys", len(data["unused"])],
            ["Undefined localization calls", len(data["undefined_rows"])],
            ["Argument mismatches", len(data["mismatch_rows"])],
            ["Keys used but not defined", len(data["undefined_key_names"])],
            ["Files with undefined calls", len(data["files_with_undef"])],
            ["Files with mismatches", len(data["files_with_mismatch"])],
        ],
    )
    f.write("### Undefined Localization Calls\n\n")
    if not data["undefined_rows"]:
        f.write("_None_\n\n")
    else:
        rows = []
        for r in data["undefined_rows"][:limit]:
            file_disp = md_code(r[0])
            lc = f"{r[1]}:{r[2]}"
            rows.append([file_disp, lc, md_code(r[3]), md_code(r[4])])
        write_markdown_table(f, ["File", "Line:Col", "Call", "Key"], rows)
        if len(data["undefined_rows"]) > limit:
            f.write(f'Showing first {limit} of {len(data["undefined_rows"])}.\n\n')
    f.write("### Argument Mismatches\n\n")
    if not data["mismatch_rows"]:
        f.write("_None_\n\n")
    else:
        rows = []
        for r in data["mismatch_rows"][:limit]:
            file_disp = md_code(r[0])
            lc = f"{r[1]}:{r[2]}"
            rows.append([file_disp, lc, md_code(r[3]), md_code(r[4]), r[5], r[6]])
        write_markdown_table(
            f, ["File", "Line:Col", "Call", "Key", "Expected args", "Got args"], rows
        )
        if len(data["mismatch_rows"]) > limit:
            f.write(f'Showing first {limit} of {len(data["mismatch_rows"])}.\n\n')
    f.write("### Unused Keys\n\n")
    if not data["unused"]:
        f.write("_None_\n\n")
    else:
        write_markdown_table(f, ["Key"], [[md_code(k)] for k in data["unused"][:limit]])
        if len(data["unused"]) > limit:
            f.write(f'Showing first {limit} of {len(data["unused"])}.\n\n')
    f.write("### Keys Used But Not Defined\n\n")
    if not data["undefined_key_names"]:
        f.write("_None_\n\n")
    else:
        write_markdown_table(
            f, ["Key"], [[md_code(k)] for k in data["undefined_key_names"][:limit]]
        )
        if len(data["undefined_key_names"]) > limit:
            f.write(f'Showing first {limit} of {len(data["undefined_key_names"])}.\n\n')


def write_framework_txt(f, data, limit):
    f.write(f'Language file: {data["language_file"]}\n')
    f.write(f'Framework dir: {data["scan_dir"]}\n\n')
    f.write("Summary\n")
    f.write("-------\n")
    f.write(f'Unique keys:                         {len(data["keys"])}\n')
    f.write(f'Total key usages found:              {data["total_hits"]}\n')
    f.write(f'Unused keys:                         {len(data["unused"])}\n')
    f.write(f'Undefined localization calls:        {len(data["undefined_rows"])}\n')
    f.write(f'Argument mismatches:                 {len(data["mismatch_rows"])}\n')
    f.write(
        f'Keys used but not defined:           {len(data["undefined_key_names"])}\n'
    )
    f.write(f'Files with undefined calls:          {len(data["files_with_undef"])}\n')
    f.write(
        f'Files with mismatches:               {len(data["files_with_mismatch"])}\n\n'
    )
    f.write("Undefined Localization Calls\n")
    f.write("-----------------------------\n")
    if data["undefined_rows"]:
        write_header(f, ["file", "line", "col", "call", "key"])
        for r in data["undefined_rows"][:limit]:
            f.write(f"{r[0]}\t{r[1]}\t{r[2]}\t{r[3]}\t{r[4]}\n")
        if len(data["undefined_rows"]) > limit:
            f.write(f'... ({len(data["undefined_rows"]) - limit} more)\n')
        f.write("\n")
    else:
        f.write("None\n\n")
    f.write("Argument Mismatches\n")
    f.write("-------------------\n")
    if data["mismatch_rows"]:
        write_header(
            f, ["file", "line", "col", "call", "key", "expected_args", "got_args"]
        )
        for r in data["mismatch_rows"][:limit]:
            f.write(f"{r[0]}\t{r[1]}\t{r[2]}\t{r[3]}\t{r[4]}\t{r[5]}\t{r[6]}\n")
        if len(data["mismatch_rows"]) > limit:
            f.write(f'... ({len(data["mismatch_rows"]) - limit} more)\n')
        f.write("\n")
    else:
        f.write("None\n\n")
    f.write("Unused Keys\n")
    f.write("-----------\n")
    if data["unused"]:
        write_header(f, ["key"])
        for k in data["unused"][:limit]:
            f.write(f"{k}\n")
        if len(data["unused"]) > limit:
            f.write(f'... ({len(data["unused"]) - limit} more)\n')
        f.write("\n")
    else:
        f.write("None\n\n")
    f.write("Keys Used But Not Defined\n")
    f.write("-------------------------\n")
    if data["undefined_key_names"]:
        write_header(f, ["key"])
        for k in data["undefined_key_names"][:limit]:
            f.write(f"{k}\n")
        if len(data["undefined_key_names"]) > limit:
            f.write(f'... ({len(data["undefined_key_names"]) - limit} more)\n')
        f.write("\n")
    else:
        f.write("None\n\n")


def write_modules_md(f, modules, limit, modules_root):
    mods = [m for m in modules if m["missing"] or m.get("duplicates_with_framework") or m.get("keys_duplicating_framework")]
    if not mods:
        f.write("_No modules with localization problems._\n\n")
        return
    summary = []
    for m in mods:
        total_missing = len(m["missing"])
        covered = len(m.get("covered_by_framework", []))
        truly_missing = len(m.get("missing_not_in_framework", []))
        duplicates = len(m.get("duplicates_with_framework", []))
        duplicating_framework = len(m.get("keys_duplicating_framework", []))
        summary.append(
            [
                md_code(m["name"]),
                md_code(relpath(m["module_dir"], modules_root)),
                total_missing,
                covered,
                truly_missing,
                duplicates,
                duplicating_framework,
            ]
        )
    f.write("### Modules Summary\n\n")
    write_markdown_table(
        f,
        ["Module", "Path", "Missing (total)", "Framework covers", "Truly missing", "Duplicates with framework", "Keys duplicating framework"],
        summary,
    )
    for m in mods:
        f.write(f'#### {m["name"]}\n\n')
        f.write(f'Language file: {md_code(m["language_file"])}\n\n')
        if m["missing"]:
            provided = m.get("covered_by_framework", [])
            if provided:
                f.write("Missing keys that framework provides (use framework values instead of adding to module)\n\n")
                rows = []
                for k in provided[:limit]:
                    val = m.get("framework_values", {}).get(k, "")
                    rows.append([md_code(k), md_code(val)])
                write_markdown_table(f, ["Key", "Framework value"], rows)
                if len(provided) > limit:
                    f.write(f"Showing first {limit} of {len(provided)}.\n\n")
            else:
                f.write("_No missing keys covered by framework._\n\n")
            missing_new = m.get("missing_not_in_framework", [])
            if missing_new:
                f.write("Keys not found in framework (add to module language file)\n\n")
                write_markdown_table(
                    f, ["Key"], [[md_code(k)] for k in missing_new[:limit]]
                )
                if len(missing_new) > limit:
                    f.write(f"Showing first {limit} of {len(missing_new)}.\n\n")
            else:
                f.write("_No truly missing keys; all are provided by framework._\n\n")
        duplicates = m.get("duplicates_with_framework", [])
        if duplicates:
            f.write("Keys duplicated with framework (consider removing these)\n\n")
            rows = []
            for k in duplicates[:limit]:
                val = m.get("lang_map", {}).get(k, "")
                rows.append([md_code(k), md_code(val)])
            write_markdown_table(f, ["Key", "Module value"], rows)
            if len(duplicates) > limit:
                f.write(f"Showing first {limit} of {len(duplicates)}.\n\n")
        duplicating_framework = m.get("keys_duplicating_framework", [])
        if duplicating_framework:
            f.write("Keys duplicating framework (can be removed from module)\n\n")
            rows = []
            for k in duplicating_framework[:limit]:
                val = m.get("lang_map", {}).get(k, "")
                rows.append([md_code(k), md_code(val)])
            write_markdown_table(f, ["Key", "Module value"], rows)
            if len(duplicating_framework) > limit:
                f.write(f"Showing first {limit} of {len(duplicating_framework)}.\n\n")
    key_to_defs = {}
    for m in modules:
        for k, v in (m.get("lang_map") or {}).items():
            key_to_defs.setdefault(k, []).append((m["name"], v))
    duplicate_keys = [k for k, lst in key_to_defs.items() if len(lst) > 1]
    conflict_keys = [
        k
        for k, lst in key_to_defs.items()
        if len(lst) > 1 and len({v for _, v in lst}) > 1
    ]
    if duplicate_keys:
        f.write("### Module Key Conflicts\n\n")
        write_markdown_table(
            f,
            ["Metric", "Value"],
            [
                ["Duplicate keys (same ID in multiple modules)", len(duplicate_keys)],
                ["Conflicting keys (same ID, different values)", len(conflict_keys)],
            ],
        )
        if conflict_keys:
            rows = []
            for k in sorted(conflict_keys)[:limit]:
                modules_list = ", ".join(sorted({m for m, _ in key_to_defs[k]}))
                rows.append([md_code(k), modules_list, len(key_to_defs[k])])
            f.write("Conflicting keys (different values)\n\n")
            write_markdown_table(f, ["Key", "Modules", "Definitions"], rows)
            if len(conflict_keys) > limit:
                f.write(f"Showing first {limit} of {len(conflict_keys)}.\n\n")
            for k in sorted(conflict_keys)[:limit]:
                f.write(f"#### {md_code(k)}\n\n")
                detrows = [(md_code(mn), md_code(v)) for mn, v in key_to_defs[k]]
                write_markdown_table(f, ["Module", "Value"], detrows)
        else:
            f.write("_No differing values among duplicated keys._\n\n")


def write_modules_txt(f, modules, limit, modules_root):
    mods = [m for m in modules if m["missing"] or m.get("duplicates_with_framework") or m.get("keys_duplicating_framework")]
    if not mods:
        f.write("No modules with localization problems.\n\n")
        return
    f.write("Modules Summary\n")
    f.write("---------------\n")
    write_header(
        f, ["module", "path", "missing_total", "framework_covers", "truly_missing", "duplicates_with_framework", "keys_duplicating_framework"]
    )
    for m in mods:
        total_missing = len(m["missing"])
        covered = len(m.get("covered_by_framework", []))
        truly_missing = len(m.get("missing_not_in_framework", []))
        duplicates = len(m.get("duplicates_with_framework", []))
        duplicating_framework = len(m.get("keys_duplicating_framework", []))
        f.write(
            f'{m["name"]}\t{relpath(m["module_dir"], modules_root)}\t{total_missing}\t{covered}\t{truly_missing}\t{duplicates}\t{duplicating_framework}\n'
        )
    f.write("\n")
    for m in mods:
        f.write(f'{m["name"]}\n')
        f.write("-" * len(m["name"]) + "\n")
        f.write(f'Language file: {m["language_file"]}\n')
        if m["missing"]:
            provided = m.get("covered_by_framework", [])
            if provided:
                f.write("Missing keys that framework provides (use framework values instead of adding to module)\n")
                write_header(f, ["key", "framework_value"])
                for k in provided[:limit]:
                    val = m.get("framework_values", {}).get(k, "")
                    f.write(f"{k}\t{val}\n")
                if len(provided) > limit:
                    f.write(f"... ({len(provided) - limit} more)\n")
                f.write("\n")
            else:
                f.write("No missing keys covered by framework.\n\n")
            missing_new = m.get("missing_not_in_framework", [])
            if missing_new:
                f.write("Keys not found in framework (add to module language file)\n")
                write_header(f, ["key"])
                for k in missing_new[:limit]:
                    f.write(f"{k}\n")
                if len(missing_new) > limit:
                    f.write(f"... ({len(missing_new) - limit} more)\n")
                f.write("\n")
            else:
                f.write("No truly missing keys; all are provided by framework.\n\n")
        duplicates = m.get("duplicates_with_framework", [])
        if duplicates:
            f.write("Keys duplicated with framework (consider removing these)\n")
            write_header(f, ["key", "module_value"])
            for k in duplicates[:limit]:
                val = m.get("lang_map", {}).get(k, "")
                f.write(f"{k}\t{val}\n")
            if len(duplicates) > limit:
                f.write(f"... ({len(duplicates) - limit} more)\n")
            f.write("\n")
        duplicating_framework = m.get("keys_duplicating_framework", [])
        if duplicating_framework:
            f.write("Keys duplicating framework (can be removed from module)\n")
            write_header(f, ["key", "module_value"])
            for k in duplicating_framework[:limit]:
                val = m.get("lang_map", {}).get(k, "")
                f.write(f"{k}\t{val}\n")
            if len(duplicating_framework) > limit:
                f.write(f"... ({len(duplicating_framework) - limit} more)\n")
            f.write("\n")
    key_to_defs = {}
    for m in modules:
        for k, v in (m.get("lang_map") or {}).items():
            key_to_defs.setdefault(k, []).append((m["name"], v))
    duplicate_keys = [k for k, lst in key_to_defs.items() if len(lst) > 1]
    conflict_keys = [
        k
        for k, lst in key_to_defs.items()
        if len(lst) > 1 and len({v for _, v in lst}) > 1
    ]
    if duplicate_keys:
        f.write("Module Key Conflicts\n")
        f.write("---------------------\n")
        write_header(f, ["metric", "value"])
        f.write(
            f"Duplicate keys (same ID in multiple modules)\t{len(duplicate_keys)}\n"
        )
        f.write(
            f"Conflicting keys (same ID, different values)\t{len(conflict_keys)}\n\n"
        )
        if conflict_keys:
            f.write("Conflicting keys (different values)\n")
            write_header(f, ["key", "modules", "definitions"])
            for k in sorted(conflict_keys)[:limit]:
                modules_list = ", ".join(sorted({m for m, _ in key_to_defs[k]}))
                f.write(f"{k}\t{modules_list}\t{len(key_to_defs[k])}\n")
            if len(conflict_keys) > limit:
                f.write(f"... ({len(conflict_keys) - limit} more)\n")
            f.write("\n")
            for k in sorted(conflict_keys)[:limit]:
                f.write(f"{k}\n")
                f.write("-" * len(k) + "\n")
                write_header(f, ["module", "value"])
                for mn, v in key_to_defs[k]:
                    f.write(f"{mn}\t{v}\n")
                f.write("\n")
        else:
            f.write("No differing values among duplicated keys.\n\n")


def lua_quote(s):
    if s is None:
        return "''"
    if "\n" in s or "\r" in s or ('"' in s and "'" in s):
        for n in range(6):
            cb = "]" + ("=" * n) + "]"
            if cb not in s:
                ob = "[" + ("=" * n) + "["
                return f"{ob}{s}{cb}"
    if '"' not in s:
        return '"' + s + '"'
    return "'" + s.replace("'", "\\'") + "'"


def get_table_keys(body):
    keys = []
    seen = set()
    r_tbl1 = re.compile(
        r'^\s*(\w+)\s*=\s*(?:"([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\'|\[=*\[.*?\]=*\])\s*[,;]?\s*(?:--[^\n]*)?$',
        re.M | re.S
    )
    r_tbl2 = re.compile(
        r'^\s*\[\s*(["\'])(.*?)\1\s*\]\s*=\s*(?:"([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\'|\[=*\[.*?\]=*\])\s*[,;]?\s*(?:--[^\n]*)?$',
        re.M | re.S
    )
    for t in r_tbl1.finditer(body):
        k = t.group(1)
        if k not in seen:
            seen.add(k)
            keys.append(k)
    for t in r_tbl2.finditer(body):
        k = t.group(2)
        if k not in seen:
            seen.add(k)
            keys.append(k)
    return keys


def delete_standalone_assignments(src, delete_keys):
    dot = re.compile(
        r'(^[ \t]*LANGUAGE\.(\w+)\s*=\s*(?:"([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\'|\[=*\[.*?\]=*\])\s*[,;]?\s*(?:--[^\n]*)?\r?\n?)',
        re.M | re.S,
    )
    idx = re.compile(
        r'(^[ \t]*LANGUAGE\[\s*(["\'])(.*?)\2\s*\]\s*=\s*(?:"([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\'|\[=*\[.*?\]=*\])\s*[,;]?\s*(?:--[^\n]*)?\r?\n?)',
        re.M | re.S,
    )
    spans = []
    for m in dot.finditer(src):
        k = m.group(2)
        if k in delete_keys:
            spans.append((m.start(1), m.end(1)))
    for m in idx.finditer(src):
        k = m.group(3)
        if k in delete_keys:
            spans.append((m.start(1), m.end(1)))
    if not spans:
        return src, 0
    spans.sort()
    merged = []
    cur_s, cur_e = spans[0]
    for s, e in spans[1:]:
        if s <= cur_e:
            if e > cur_e:
                cur_e = e
        else:
            merged.append((cur_s, cur_e))
            cur_s, cur_e = s, e
    merged.append((cur_s, cur_e))
    out = []
    last = 0
    for a, b in merged:
        out.append(src[last:a])
        last = b
    out.append(src[last:])
    return "".join(out), len(merged)


def replace_table_entries(src, keep_keys, values):
    r_tbl = re.compile(r"(^[ \t]*(?:local\s+)?LANGUAGE\s*=\s*\{)", re.M)
    pos = 0
    total_replaced = 0
    while True:
        m = r_tbl.search(src, pos)
        if not m:
            break
        open_brace = src.find("{", m.start())
        body, endpos = extract_block(src, open_brace, "{", "}")
        if body is None:
            pos = m.end()
            continue
        line_start = src.rfind("\n", 0, m.start())
        line_start = 0 if line_start < 0 else line_start + 1
        indent = src[line_start : m.start()]
        indent2 = indent + "    "
        tbl_keys = get_table_keys(body)
        kept = [k for k in tbl_keys if k in keep_keys]
        lines = []
        for k in kept:
            if re.match(r"^[A-Za-z_]\w*$", k):
                keyexpr = k
            else:
                keyexpr = f'["{k}"]'
            v = values.get(k, "")
            lines.append(f"{indent2}{keyexpr} = {lua_quote(v)},")
        new_body = ""
        if lines:
            new_body = "\n" + "\n".join(lines) + "\n" + indent
        src = src[: open_brace + 1] + new_body + src[endpos:]
        pos = open_brace + 1 + len(new_body)
        total_replaced += 1
    return src, total_replaced


def search_for_language_keys_in_code(module_dir, missing_keys):
    print(f"    Searching for LANGUAGE key definitions in {module_dir}...")
    found_keys = {}
    used_keys = {}
    language_files = []
    for root, _, files in os.walk(module_dir):
        for filename in files:
            if not filename.lower().endswith('.lua'):
                continue
            filepath = os.path.join(root, filename)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                if 'LANGUAGE' in content:
                    language_files.append((filepath, content))
                for key in missing_keys:
                    if key in content:
                        print(f"      Found key '{key}' in {os.path.basename(filepath)}")
                        lines = content.split('\n')
                        c = 0
                        for i, line in enumerate(lines, 1):
                            if key in line:
                                print(f"        Line {i}: {line.strip()}")
                                c += 1
                                if c >= 5:
                                    break
                        print()
                patterns = [
                    (rf'LANGUAGE\.(\w+)\s*=\s*["\'][^"\']*["\']', 'LANGUAGE.key = "value"'),
                    (rf'LANGUAGE\[["\']([^"\']+)["\']\]\s*=\s*["\'][^"\']*["\']', 'LANGUAGE["key"] = "value"'),
                    (rf'(\w+)\s*=\s*["\'][^"\']*["\'],?\s*$', 'key = "value" (in table)'),
                    (rf'\[["\']([^"\']+)["\']\]\s*=\s*["\'][^"\']*["\'],?\s*$', '["key"] = "value" (in table)'),
                ]
                for pattern, desc in patterns:
                    matches = re.findall(pattern, content, re.MULTILINE)
                    for match in matches:
                        key = match[0] if isinstance(match, tuple) else match
                        if key in missing_keys:
                            if key not in found_keys:
                                found_keys[key] = []
                            found_keys[key].append(f"{os.path.basename(filepath)} ({desc})")
                usage_patterns = [
                    (rf'L\(["\']([^"\']+)["\']\)', 'L("key")'),
                    (rf'notifyLocalized\(["\']([^"\']+)["\']\)', 'notifyLocalized("key")'),
                    (rf'LANGUAGE\[["\']([^"\']+)["\']\]', 'LANGUAGE["key"]'),
                    (rf'LANGUAGE\.(\w+)', 'LANGUAGE.key'),
                ]
                for pattern, desc in usage_patterns:
                    matches = re.findall(pattern, content, re.MULTILINE)
                    for match in matches:
                        key = match[0] if isinstance(match, tuple) else match
                        if key in missing_keys:
                            if key not in used_keys:
                                used_keys[key] = []
                            used_keys[key].append(f"{os.path.basename(filepath)} ({desc})")
            except Exception as e:
                print(f"    Warning: Could not read {filepath}: {e}")
                continue
    if language_files:
        print(f"    Found {len(language_files)} files containing 'LANGUAGE':")
        for filepath, content in language_files[:3]:
            print(f"      {os.path.basename(filepath)}:")
            lines = content.split('\n')
            c = 0
            for i, line in enumerate(lines, 1):
                if 'LANGUAGE' in line:
                    print(f"        Line {i}: {line.strip()}")
                    c += 1
                    if c >= 10:
                        print(f"        ... and more LANGUAGE lines")
                        break
            print()
    if found_keys:
        print(f"    Found {len(found_keys)} missing keys DEFINED in code files:")
        for key, locations in found_keys.items():
            print(f"      {key}: {', '.join(locations)}")
    else:
        print(f"    No missing keys found DEFINED in code files.")
    if used_keys:
        print(f"    Found {len(used_keys)} missing keys USED in code files:")
        for key, locations in used_keys.items():
            print(f"      {key}: {', '.join(locations)}")
    else:
        print(f"    No missing keys found USED in code files.")
    return found_keys, used_keys


def remove_missing_keys_from_code(module_dir, missing_keys):
    removed_count = 0
    missing_keys_set = set(missing_keys)
    print(f"    Scanning {module_dir} for missing keys: {list(missing_keys_set)[:5]}...")
    for root, _, files in os.walk(module_dir):
        for filename in files:
            if not filename.lower().endswith('.lua'):
                continue
            filepath = os.path.join(root, filename)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                original_content = content
                file_modified = False
                for key in missing_keys_set:
                    patterns = [
                        rf'^\s*LANGUAGE\.{re.escape(key)}\s*=\s*["\'][^"\']*["\']\s*(?:[,;]?\s*(?:--[^\n]*)?)?$',
                        rf'^\s*{re.escape(key)}\s*=\s*["\'][^"\']*["\']\s*(?:[,;]?\s*(?:--[^\n]*)?)?$',
                        rf'^\s*LANGUAGE\[["\']{re.escape(key)}["\']\]\s*=\s*["\'][^"\']*["\']\s*(?:[,;]?\s*(?:--[^\n]*)?)?$',
                        rf'^\s*\[["\']{re.escape(key)}["\']\]\s*=\s*["\'][^"\']*["\']\s*(?:[,;]?\s*(?:--[^\n]*)?)?$',
                    ]
                    for pattern in patterns:
                        if re.search(pattern, content, flags=re.MULTILINE):
                            content = re.sub(pattern, '', content, flags=re.MULTILINE)
                            file_modified = True
                if file_modified:
                    content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
                    content = re.sub(r'^\s*\n+', '', content)
                    content = re.sub(r'\n+\s*$', '\n', content)
                    with open(filepath, 'w', encoding='utf-8', newline='') as f:
                        f.write(content)
                    removed_count += max(0, original_content.count('\n') - content.count('\n'))
                    print(f"      Modified {filepath}")
            except Exception as e:
                print(f"    Warning: Could not process {filepath}: {e}")
                continue
    return removed_count


def cleanup_language_file(language_file, unused_keys, values):
    if not unused_keys:
        return 0, 0
    with open(language_file, "r", encoding="utf-8", errors="ignore") as f:
        src = f.read()
    all_keys = set(values.keys())
    keep_keys = all_keys - set(unused_keys)
    src, replaced = replace_table_entries(src, keep_keys, values)
    src, removed = delete_standalone_assignments(src, set(unused_keys))
    with open(language_file, "w", encoding="utf-8", newline="") as f:
        f.write(src)
    return replaced, removed


def debug_language_file_parsing(language_file, keys_to_delete):
    print(f"\n=== DEBUG: Parsing {os.path.basename(language_file)} ===")
    try:
        with open(language_file, 'r', encoding='utf-8', errors='ignore') as f:
            src = f.read()
        print(f"File size: {len(src)} characters")
        print(f"Keys to delete: {keys_to_delete}")
        print("\n--- Testing get_table_keys function ---")
        r_tbl_start = re.compile(r"\bLANGUAGE\s*=\s*\{", re.S)
        pos = 0
        table_count = 0
        while True:
            m = r_tbl_start.search(src, pos)
            if not m:
                break
            open_brace = src.find("{", m.start())
            body, endpos = extract_block(src, open_brace, "{", "}")
            if body is None:
                pos = m.end()
                continue
            table_count += 1
            print(f"\nTable {table_count}:")
            print(f"  Body length: {len(body)} characters")
            print(f"  Body preview: {repr(body[:200])}...")
            extracted_keys = get_table_keys(body)
            print(f"  Extracted keys: {extracted_keys}")
            found_keys_to_delete = [k for k in keys_to_delete if k in extracted_keys]
            if found_keys_to_delete:
                print(f"  Keys to delete found: {found_keys_to_delete}")
            else:
                print(f"  No keys to delete found in this table")
            pos = endpos + 1
        print(f"\nTotal tables found: {table_count}")
        print("\n--- Testing delete_standalone_assignments function ---")
        for key in keys_to_delete:
            patterns = [
                rf'LANGUAGE\.{re.escape(key)}\s*=',
                rf'LANGUAGE\[["\']{re.escape(key)}["\']\]\s*=',
            ]
            for pattern in patterns:
                matches = re.findall(pattern, src)
                if matches:
                    print(f"  Found standalone assignment for '{key}': {len(matches)} matches")
                    lines = src.split('\n')
                    c = 0
                    for i, line in enumerate(lines, 1):
                        if re.search(pattern, line):
                            print(f"    Line {i}: {line.strip()}")
                            c += 1
                            if c >= 5:
                                break
        print("\n--- Testing replace_table_entries function ---")
        dummy_values = {k: f"DUMMY_VALUE_{k}" for k in keys_to_delete}
        dummy_values.update({k: f"KEEP_VALUE_{k}" for k in ["keep1", "keep2"]})
        all_keys = set(keys_to_delete) | {"keep1", "keep2"}
        keep_keys = all_keys - set(keys_to_delete)
        print(f"  All keys: {all_keys}")
        print(f"  Keep keys: {keep_keys}")
        print(f"  Delete keys: {keys_to_delete}")
        print("  (replace_table_entries would rebuild tables with keep_keys only)")
    except Exception as e:
        print(f"Error debugging file: {e}")
    print("=== END DEBUG ===\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--framework-gamemode-dir", default=DEFAULT_FRAMEWORK_GAMEMODE_DIR)
    p.add_argument("--framework-languages-dir", default=DEFAULT_FRAMEWORK_LANGUAGES_DIR)
    p.add_argument("--modules-root", default=DEFAULT_MODULES_ROOT)
    p.add_argument("--modules-dir", default=DEFAULT_MODULES_DIR)
    p.add_argument("--devmodules-dir", default=DEFAULT_DEVMODULES_DIR)
    p.add_argument("--out-pattern", default=DEFAULT_OUT_PATTERN)
    p.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    p.add_argument("--format", choices=["auto", "md", "txt"], default="auto")
    p.add_argument("--debug", action="store_true")
    p.add_argument("-y", "--yes", action="store_true")
    p.add_argument("--delete-unused", action="store_true")
    p.add_argument("--remove-duplicates", action="store_true")
    p.add_argument("--remove-missing-from-code", action="store_true")
    a = p.parse_args()
    if not os.path.isdir(a.framework_gamemode_dir):
        print("Framework dir not found", file=sys.stderr)
        sys.exit(1)
    if not os.path.isdir(a.framework_languages_dir):
        print("Framework languages dir not found", file=sys.stderr)
        sys.exit(1)
    if not os.path.isdir(a.modules_root):
        print("Modules root not found", file=sys.stderr)
        sys.exit(1)
    names = [
        f for f in os.listdir(a.framework_languages_dir) if f.lower().endswith(".lua")
    ]
    if not names:
        print("No framework language files found", file=sys.stderr)
        sys.exit(1)
    fmt = a.format
    if fmt == "auto":
        ext = os.path.splitext(a.out_pattern)[1].lower()
        fmt = "md" if ext in (".md", ".markdown") else "txt"
    any_unused = False
    any_duplicates = False
    framework_results = []
    modules_results = []
    per_lang_dup_counts = {}
    framework_by_lang = {}
    for fname in sorted(names):
        lf = os.path.join(a.framework_languages_dir, fname)
        lang = os.path.splitext(os.path.basename(lf))[0]
        framework = analyze_data(lf, a.framework_gamemode_dir)
        framework_results.append((lang, framework))
        framework_by_lang[lang] = framework
        framework_key_set = set(framework["keys"])
        framework_lang_map = framework["lang_map"]
        modules = []
        module_dirs = [a.modules_root, a.modules_dir, a.devmodules_dir]
        for module_dir in module_dirs:
            if not os.path.isdir(module_dir):
                continue
            for mname in sorted(os.listdir(module_dir)):
                mdir = os.path.join(module_dir, mname)
                if not os.path.isdir(mdir):
                    continue
                mlf = os.path.join(mdir, "languages", f"{lang}.lua")
                if not os.path.isfile(mlf):
                    continue
                mdata = analyze_data(mlf, mdir)
                missing = mdata["undefined_key_names"]
                covered = [k for k in missing if k in framework_key_set]
                missing_new = [k for k in missing if k not in framework_key_set]
                framework_values = {k: framework_lang_map.get(k, "") for k in covered}
                module_defined_keys = set(mdata["lang_map"].keys())
                duplicates_with_framework = sorted(module_defined_keys & framework_key_set)
                if duplicates_with_framework:
                    any_duplicates = True
                modules.append(
                    {
                        "name": f"{os.path.basename(module_dir)}/{mname}",
                        "module_dir": mdir,
                        "language_file": mlf,
                        "missing": missing,
                        "covered_by_framework": covered,
                        "missing_not_in_framework": missing_new,
                        "framework_values": framework_values,
                        "unused": mdata["unused"],
                        "lang_map": mdata["lang_map"],
                        "duplicates_with_framework": duplicates_with_framework,
                        "keys_duplicating_framework": list(module_defined_keys & framework_key_set),
                    }
                )
                if mdata["unused"]:
                    any_unused = True
        modules_results.append((lang, modules))
        if framework["unused"]:
            any_unused = True
        out_report = a.out_pattern.format(name=lang)
        dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        modules_with_problems = [m for m in modules if m["missing"] or m.get("duplicates_with_framework") or m.get("keys_duplicating_framework")]
        if fmt == "md":
            with open(out_report, "w", encoding="utf-8", newline="") as f:
                f.write(f"# Localization Analysis Report ({lang})\n\n")
                f.write(f"Generated: {md_code(dt)}\n\n")
                f.write("## Framework\n\n")
                write_framework_md(f, framework, a.limit)
                f.write("## Modules\n\n")
                write_modules_md(f, modules_with_problems, a.limit, a.modules_root)
        else:
            with open(out_report, "w", encoding="utf-8", newline="") as f:
                f.write(f"Localization Analysis Report ({lang})\n")
                f.write(
                    "=" * (len("Localization Analysis Report") + len(lang) + 3) + "\n\n"
                )
                f.write(f"Generated: {dt}\n\n")
                f.write("Framework\n")
                f.write("---------\n")
                write_framework_txt(f, framework, a.limit)
                f.write("Modules\n")
                f.write("-------\n")
                write_modules_txt(f, modules_with_problems, a.limit, a.modules_root)
        print(out_report)
        per_lang_dup_counts[lang] = sum(len(m["duplicates_with_framework"]) for m in modules)
    if any_unused:
        proceed_unused = a.yes or a.delete_unused
        if not proceed_unused:
            if sys.stdin and sys.stdin.isatty():
                try:
                    ans = input("Delete unused localizations in framework and modules? [y/N]: ").strip().lower()
                except EOFError:
                    ans = "n"
            else:
                ans = "n"
            proceed_unused = ans in ("y", "yes")
        if proceed_unused:
            for lang, framework in framework_results:
                if framework["unused"]:
                    replaced, removed = cleanup_language_file(
                        framework["language_file"],
                        framework["unused"],
                        framework["lang_map"],
                    )
                    print(
                        f'{lang}: framework {os.path.basename(framework["language_file"])} cleaned ({replaced} table(s) rebuilt, {removed} standalone removed)'
                    )
            for lang, modules in modules_results:
                for m in modules:
                    if m["unused"]:
                        replaced, removed = cleanup_language_file(
                            m["language_file"], m["unused"], m["lang_map"]
                        )
                        print(
                            f'{lang}: module {m["name"]} cleaned ({replaced} table(s) rebuilt, {removed} standalone removed)'
                        )
        else:
            print("No deletions made.")
    else:
        print("No unused localizations found.")
    for lang, framework in framework_results:
        print(f'{lang}: framework unused keys = {len(framework["unused"])}')
    total_dups = 0
    for lang, _modules in modules_results:
        cnt = per_lang_dup_counts.get(lang, 0)
        total_dups += cnt
        print(f"{lang}: duplicated module entries overlapping framework = {cnt}")
    if total_dups > 0:
        proceed_dups = a.yes or a.remove_duplicates
        if not proceed_dups:
            if sys.stdin and sys.stdin.isatty():
                try:
                    ans = input("Remove duplicated module localization entries? [y/N]: ").strip().lower()
                except EOFError:
                    ans = "n"
            else:
                ans = "n"
            proceed_dups = ans in ("y", "yes")
        if proceed_dups:
            for lang, modules in modules_results:
                for m in modules:
                    dups = m.get("duplicates_with_framework") or []
                    if not dups:
                        continue
                    replaced, removed = cleanup_language_file(
                        m["language_file"], dups, m["lang_map"]
                    )
                    print(
                        f'{lang}: module {m["name"]} de-duplicated ({replaced} table(s) rebuilt, {removed} standalone removed, {len(dups)} keys targeted)'
                    )
        else:
            print("No duplicated entries removed.")
    else:
        print("No duplicated module localization entries found.")
    total_framework_provided = 0
    total_missing_covered_by_framework = 0
    for lang, modules in modules_results:
        for m in modules:
            module_keys = set(m.get("lang_map", {}).keys())
            fk = set(framework_by_lang.get(lang, {}).get("keys", []))
            existing_duplicates = list(module_keys & fk)
            missing_covered = m.get("covered_by_framework", [])
            total_framework_provided += len(existing_duplicates)
            total_missing_covered_by_framework += len(missing_covered)
    total_issues = total_framework_provided + total_missing_covered_by_framework
    if total_issues > 0:
        print(f"\nFramework localization analysis:")
        print(f"  • {total_framework_provided} existing keys in modules that duplicate framework")
        print(f"  • {total_missing_covered_by_framework} missing keys in modules that framework provides")
        print(f"  • Total: {total_issues} keys that can use framework values")
        proceed_existing_dups = a.yes or a.remove_duplicates
        if total_framework_provided > 0:
            if not proceed_existing_dups:
                if sys.stdin and sys.stdin.isatty():
                    try:
                        ans = input("Delete existing keys that duplicate framework from modules? [y/N]: ").strip().lower()
                    except EOFError:
                        ans = "n"
                else:
                    ans = "n"
                proceed_existing_dups = ans in ("y", "yes")
            if proceed_existing_dups:
                for lang, modules in modules_results:
                    for m in modules:
                        module_keys = set(m.get("lang_map", {}).keys())
                        fk = set(framework_by_lang.get(lang, {}).get("keys", []))
                        existing_duplicates = list(module_keys & fk)
                        if existing_duplicates:
                            if a.debug:
                                print(f"\n=== DEBUG: Cleaning up {m['name']} ===")
                                print(f"Keys to remove: {existing_duplicates}")
                                debug_language_file_parsing(m["language_file"], existing_duplicates)
                            replaced, removed = cleanup_language_file(
                                m["language_file"], existing_duplicates, m["lang_map"]
                            )
                            if a.debug:
                                print(f"Cleanup results: {replaced} table(s) rebuilt, {removed} standalone removed")
                                if replaced == 0 and removed == 0:
                                    print("WARNING: No keys were removed! This might indicate a parsing issue.")
                            print(
                                f'{lang}: module {m["name"]} existing duplicates removed ({replaced} table(s) rebuilt, {removed} standalone removed, {len(existing_duplicates)} keys targeted)'
                            )
            else:
                print("No existing duplicate keys removed.")
        if total_missing_covered_by_framework > 0:
            print(f"\nNote: {total_missing_covered_by_framework} missing keys in modules are provided by the framework.")
            print("These keys don't need to be added to modules - they can use framework values directly.")
            print("To use framework values, remove any LANGUAGE.key = 'value' lines for these keys from your code.")
            print("The framework will automatically provide the values when the keys are requested.")
            print(f"\nExamples of missing keys that framework provides:")
            count = 0
            for lang, modules in modules_results:
                if count >= 5:
                    break
                for m in modules:
                    if count >= 5:
                        break
                    missing_covered = m.get("covered_by_framework", [])
                    if missing_covered:
                        for key in missing_covered[:2]:
                            if count >= 5:
                                break
                            framework_val = m.get("framework_values", {}).get(key, "")
                            print(f"  • {key} = '{framework_val}' (from framework)")
                            count += 1
            if total_missing_covered_by_framework > 5:
                print(f"  ... and {total_missing_covered_by_framework - 5} more keys")
            print(f"\nFull details are available in the generated reports.")
            proceed_missing_from_code = a.yes or a.remove_missing_from_code
            if not proceed_missing_from_code:
                if sys.stdin and sys.stdin.isatty():
                    try:
                        ans = input("Remove missing keys that framework provides from code files? [y/N]: ").strip().lower()
                    except EOFError:
                        ans = "n"
                else:
                    ans = "n"
                proceed_missing_from_code = ans in ("y", "yes")
            if proceed_missing_from_code:
                print("Scanning code files for missing keys that framework provides...")
                total_found = 0
                total_used = 0
                for lang, modules in modules_results:
                    for m in modules:
                        missing_covered = m.get("covered_by_framework", [])
                        if not missing_covered:
                            continue
                        found_keys, used_keys = search_for_language_keys_in_code(m["module_dir"], missing_covered)
                        total_found += len(found_keys)
                        total_used += len(used_keys)
                print(f"\nSummary:")
                print(f"  • {total_found} missing keys are DEFINED in code files (can be removed)")
                print(f"  • {total_used} missing keys are USED in code files (framework will provide values)")
                print(f"  • {total_missing_covered_by_framework} total missing keys that framework provides")
                if total_found == 0:
                    print(f"\nNo existing LANGUAGE key definitions found for the {total_missing_covered_by_framework} missing keys.")
                    print("This means your code is already correctly using framework values!")
                else:
                    print(f"\nFound {total_found} missing keys that are defined in code files.")
                    print("Now removing these definitions...")
                    removed_count = 0
                    for lang, modules in modules_results:
                        for m in modules:
                            missing_covered = m.get("covered_by_framework", [])
                            if not missing_covered:
                                continue
                            module_dir = m["module_dir"]
                            if a.debug:
                                print(f"\n=== DEBUG: Processing missing keys for {m['name']} ===")
                                print(f"Missing keys covered by framework: {missing_covered}")
                                print(f"Module directory: {module_dir}")
                            removed_from_module = remove_missing_keys_from_code(module_dir, missing_covered)
                            if removed_from_module > 0:
                                print(f"  {lang}: {m['name']} - removed {removed_from_module} missing key references")
                                removed_count += removed_from_module
                            elif a.debug:
                                print(f"  {lang}: {m['name']} - no missing key references found/removed")
                    if removed_count > 0:
                        print(f"\nTotal: Removed {removed_count} missing key references from code files.")
                    else:
                        print("No missing key references were removed from code files.")
            else:
                print("No missing key references removed from code files.")
    else:
        print("No keys provided by framework found in modules.")


if __name__ == "__main__":
    main()

    
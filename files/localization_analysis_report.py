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
    return str(s).replace("|", r"\|")


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
    mods = [m for m in modules if m["missing"]]
    if not mods:
        f.write("_No modules with missing keys._\n\n")
        return
    summary = []
    for m in mods:
        total_missing = len(m["missing"])
        covered = len(m.get("covered_by_framework", []))
        truly_missing = len(m.get("missing_not_in_framework", []))
        summary.append(
            [
                md_code(m["name"]),
                md_code(relpath(m["module_dir"], modules_root)),
                total_missing,
                covered,
                truly_missing,
            ]
        )
    f.write("### Modules Summary\n\n")
    write_markdown_table(
        f,
        ["Module", "Path", "Missing (total)", "Provided by framework", "Truly missing"],
        summary,
    )
    for m in mods:
        f.write(f'#### {m["name"]}\n\n')
        f.write(f'Language file: {md_code(m["language_file"])}\n\n')
        provided = m.get("covered_by_framework", [])
        if provided:
            f.write("Keys provided by framework (consider reusing these)\n\n")
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
    f.write("### Module Key Conflicts\n\n")
    if not duplicate_keys:
        f.write("_None_\n\n")
    else:
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
    mods = [m for m in modules if m["missing"]]
    if not mods:
        f.write("No modules with missing keys.\n\n")
        return
    f.write("Modules Summary\n")
    f.write("---------------\n")
    write_header(
        f, ["module", "path", "missing_total", "provided_by_framework", "truly_missing"]
    )
    for m in mods:
        total_missing = len(m["missing"])
        covered = len(m.get("covered_by_framework", []))
        truly_missing = len(m.get("missing_not_in_framework", []))
        f.write(
            f'{m["name"]}\t{relpath(m["module_dir"], modules_root)}\t{total_missing}\t{covered}\t{truly_missing}\n'
        )
    f.write("\n")
    for m in mods:
        f.write(f'{m["name"]}\n')
        f.write("-" * len(m["name"]) + "\n")
        f.write(f'Language file: {m["language_file"]}\n')
        provided = m.get("covered_by_framework", [])
        if provided:
            f.write("Keys provided by framework (consider reusing these)\n")
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
    f.write("Module Key Conflicts\n")
    f.write("---------------------\n")
    if not duplicate_keys:
        f.write("None\n\n")
    else:
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
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"


def get_table_keys(body):
    keys = []
    seen = set()
    r_tbl1 = re.compile(
        r'(\w+)\s*=\s*(?:("([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\'|\[=*\[.*?\]=*\]))', re.S
    )
    r_tbl2 = re.compile(
        r'\[\s*(["\'])(.*?)\1\s*\]\s*=\s*(?:("([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\'|\[=*\[.*?\]=*\]))',
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
    return keys


def delete_standalone_assignments(src, delete_keys):
    dot = re.compile(
        r'(^[ \t]*LANGUAGE\.(\w+)\s*=\s*(?:"([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\'|\[=*\[.*?\]=*\])[ \t]*\r?\n?)',
        re.M | re.S,
    )
    idx = re.compile(
        r'(^[ \t]*LANGUAGE\[\s*(["\'])(.*?)\2\s*\]\s*=\s*(?:"([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\'|\[=*\[.*?\]=*\])[ \t]*\r?\n?)',
        re.M | re.S,
    )
    spans = []
    removed = 0
    for m in dot.finditer(src):
        k = m.group(2)
        if k in delete_keys:
            spans.append((m.start(1), m.end(1)))
            removed += 1
    for m in idx.finditer(src):
        k = m.group(3)
        if k in delete_keys:
            spans.append((m.start(1), m.end(1)))
            removed += 1
    if not spans:
        return src, 0
    spans.sort(reverse=True)
    s = src
    for a, b in spans:
        s = s[:a] + s[b:]
    return s, removed


def replace_table_entries(src, keep_keys, values):
    r_tbl = re.compile(r"(^[ \t]*LANGUAGE\s*=\s*\{)", re.M)
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


def cleanup_language_file(language_file, unused_keys, values):
    if not unused_keys:
        return 0, 0
    with open(language_file, "r", encoding="utf-8", errors="ignore") as f:
        src = f.read()
    ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    bak = f"{language_file}.bak.{ts}"
    shutil.copyfile(language_file, bak)
    all_keys = set(values.keys())
    keep_keys = all_keys - set(unused_keys)
    src, replaced = replace_table_entries(src, keep_keys, values)
    src, removed = delete_standalone_assignments(src, set(unused_keys))
    with open(language_file, "w", encoding="utf-8", newline="") as f:
        f.write(src)
    return replaced, removed


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--framework-gamemode-dir", default=DEFAULT_FRAMEWORK_GAMEMODE_DIR)
    p.add_argument("--framework-languages-dir", default=DEFAULT_FRAMEWORK_LANGUAGES_DIR)
    p.add_argument("--modules-root", default=DEFAULT_MODULES_ROOT)
    p.add_argument("--out-pattern", default=DEFAULT_OUT_PATTERN)
    p.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    p.add_argument("--format", choices=["auto", "md", "txt"], default="auto")
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
    framework_results = []
    modules_results = []
    for fname in sorted(names):
        lf = os.path.join(a.framework_languages_dir, fname)
        lang = os.path.splitext(os.path.basename(lf))[0]
        framework = analyze_data(lf, a.framework_gamemode_dir)
        framework_results.append((lang, framework))
        framework_key_set = set(framework["keys"])
        framework_lang_map = framework["lang_map"]
        modules = []
        for mname in sorted(os.listdir(a.modules_root)):
            mdir = os.path.join(a.modules_root, mname)
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
            modules.append(
                {
                    "name": mname,
                    "module_dir": mdir,
                    "language_file": mlf,
                    "missing": missing,
                    "covered_by_framework": covered,
                    "missing_not_in_framework": missing_new,
                    "framework_values": framework_values,
                    "unused": mdata["unused"],
                    "lang_map": mdata["lang_map"],
                }
            )
            if mdata["unused"]:
                any_unused = True
        modules_results.append((lang, modules))
        if framework["unused"]:
            any_unused = True
        out_report = a.out_pattern.format(name=lang)
        dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if fmt == "md":
            with open(out_report, "w", encoding="utf-8", newline="") as f:
                f.write(f"# Localization Analysis Report ({lang})\n\n")
                f.write(f"Generated: {md_code(dt)}\n\n")
                f.write("## Framework\n\n")
                write_framework_md(f, framework, a.limit)
                f.write("## Modules\n\n")
                write_modules_md(f, modules, a.limit, a.modules_root)
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
                write_modules_txt(f, modules, a.limit, a.modules_root)
        print(out_report)
    if any_unused:
        try:
            ans = (
                input("Delete unused localizations in framework and modules? [y/N]: ")
                .strip()
                .lower()
            )
        except EOFError:
            ans = "n"
        if ans in ("y", "yes"):
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


if __name__ == "__main__":
    main()

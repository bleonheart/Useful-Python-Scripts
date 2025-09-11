import sys, os, argparse

def read_lines(p):
    try:
        with open(p, "r", encoding="utf-8") as f:
            return [l.rstrip("\n") for l in f]
    except:
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            return [l.rstrip("\n") for l in f]

def write_text(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)

def clean_path(s):
    s = s.replace("\ufeff", "").strip().strip('"\'')
    cut = len(s)
    for sep in ("|", ","):
        idx = s.find(sep)
        if idx != -1:
            cut = min(cut, idx)
    s = s[:cut].strip().strip('"\'').rstrip(" ,;:\t")
    return os.path.normpath(s)

def parse_list_file(p):
    out = []
    for l in read_lines(p):
        s = l.strip()
        if not s:
            continue
        if "|" in s or "," in s:
            fp = clean_path(s)
            if fp:
                out.append(fp)
            continue
        parts = s.split()
        if len(parts) >= 3:
            fp = clean_path(" ".join(parts[:-2]))
            if fp:
                out.append(fp)
            continue
        if parts:
            fp = clean_path(parts[0])
            if fp:
                out.append(fp)
    return sorted(set(out))

def is_ident_start(c):
    return c == "_" or ("A" <= c <= "Z") or ("a" <= c <= "z")

def is_ident_char(c):
    return is_ident_start(c) or ("0" <= c <= "9")

def match_long_bracket(s, i):
    j = i + 1
    eq = 0
    while j < len(s) and s[j] == "=":
        eq += 1
        j += 1
    if j < len(s) and s[j] == "[":
        k = j + 1
        end_seq = "]" + ("=" * eq) + "]"
        idx = s.find(end_seq, k)
        return (idx + len(end_seq)) if idx != -1 else len(s)
    return i + 1

def tokenize(s):
    i = 0
    n = len(s)
    tokens = []
    keywords = {"function","if","then","elseif","else","for","while","do","end","repeat","until","local","return","break"}
    while i < n:
        c = s[i]
        if c in " \t\r\f\v\n":
            i += 1
            continue
        if c == "-" and i + 1 < n and s[i+1] == "-":
            if i + 2 < n and s[i+2] == "[":
                j = match_long_bracket(s, i + 2)
                i = j
            else:
                j = s.find("\n", i + 2)
                i = n if j == -1 else j + 1
            continue
        if c in ("'", '"'):
            q = c
            j = i + 1
            while j < n:
                if s[j] == "\\":
                    j += 2
                    continue
                if s[j] == q:
                    j += 1
                    break
                j += 1
            i = j
            continue
        if c == "[":
            j = match_long_bracket(s, i)
            if j > i + 1:
                i = j
                continue
        if c == "." and i + 2 < n and s[i+1] == "." and s[i+2] == ".":
            tokens.append(("vararg","...",i,i+3))
            i += 3
            continue
        if is_ident_start(c):
            j = i + 1
            while j < n and is_ident_char(s[j]):
                j += 1
            val = s[i:j]
            t = "keyword" if val in keywords else "ident"
            tokens.append((t, val, i, j))
            i = j
            continue
        if c in "(),.:;[]{}=":
            tokens.append(("punct", c, i, i+1))
            i += 1
            continue
        i += 1
    return tokens

def transform_source(src):
    tokens = tokenize(src)
    edits = []
    i = 0
    param_indices = set()
    while i < len(tokens):
        t = tokens[i]
        if t[0] == "keyword" and t[1] == "function":
            j = i + 1
            while j < len(tokens) and not (tokens[j][0] == "punct" and tokens[j][1] == "("):
                j += 1
            if j >= len(tokens):
                i += 1
                continue
            paren_open = j
            depth = 1
            k = j + 1
            while k < len(tokens) and depth > 0:
                tt = tokens[k]
                if tt[0] == "punct" and tt[1] == "(":
                    depth += 1
                elif tt[0] == "punct" and tt[1] == ")":
                    depth -= 1
                    if depth == 0:
                        break
                k += 1
            if k >= len(tokens):
                i += 1
                continue
            paren_close = k
            params = []
            commas = []
            p = paren_open + 1
            while p < paren_close:
                tt = tokens[p]
                if tt[0] == "ident":
                    params.append({"name":tt[1],"start":tt[2],"end":tt[3],"tok":p})
                    param_indices.add(p)
                elif tt[0] == "vararg":
                    params.append({"name":"...","start":tt[2],"end":tt[3],"tok":p})
                elif tt[0] == "punct" and tt[1] == ",":
                    commas.append((tt[2],tt[3]))
                p += 1
            stack = ["function"]
            expecting_do = False
            used = set()
            m = paren_close + 1
            while m < len(tokens) and stack:
                tt = tokens[m]
                if tt[0] == "ident":
                    used.add(tt[1])
                elif tt[0] == "keyword":
                    v = tt[1]
                    if v == "function":
                        stack.append("function")
                    elif v == "if":
                        stack.append("if")
                    elif v == "for":
                        stack.append("for")
                        expecting_do = True
                    elif v == "while":
                        stack.append("while")
                        expecting_do = True
                    elif v == "do":
                        if expecting_do:
                            expecting_do = False
                        else:
                            stack.append("do")
                    elif v == "repeat":
                        stack.append("repeat")
                    elif v == "until":
                        if stack and stack[-1] == "repeat":
                            stack.pop()
                    elif v == "end":
                        if stack:
                            top = stack.pop()
                            if top != "repeat" and not stack:
                                break
                m += 1
            has_right = False
            for idx in range(len(params)-1,-1,-1):
                nm = params[idx]["name"]
                if nm in ("...", "_"):
                    has_right = True
                    continue
                if nm in used:
                    has_right = True
                    continue
                if has_right:
                    edits.append((params[idx]["start"], params[idx]["end"], "_"))
                else:
                    if idx > 0 and len(commas) >= idx:
                        cs, ce = commas[idx-1]
                        edits.append((cs, params[idx]["end"], ""))
                    else:
                        edits.append((params[idx]["start"], params[idx]["end"], ""))
            i = m + 1
        else:
            i += 1
    local_decl_indices = set()
    local_stmts = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t[0] == "keyword" and t[1] == "local":
            j = i + 1
            if j < len(tokens) and tokens[j][0] == "keyword" and tokens[j][1] == "function":
                i += 1
                continue
            vars_list = []
            p = j
            expect_ident = True
            while p < len(tokens):
                tt = tokens[p]
                if expect_ident and tt[0] == "ident":
                    vars_list.append({"name":tt[1],"start":tt[2],"end":tt[3],"tok":p})
                    local_decl_indices.add(p)
                    expect_ident = False
                    p += 1
                    continue
                if not expect_ident and tt[0] == "punct" and tt[1] == ",":
                    expect_ident = True
                    p += 1
                    continue
                break
            eq = p < len(tokens) and tokens[p][0] == "punct" and tokens[p][1] == "="
            start_pos = t[2]
            ls = src.rfind("\n", 0, start_pos)
            prefix = src[(ls + 1 if ls != -1 else 0):start_pos]
            removal_start = (ls + 1 if ls != -1 and prefix.strip() == "" else start_pos)
            le = src.find("\n", start_pos)
            removal_end = (le + 1) if le != -1 else len(src)
            if vars_list:
                local_stmts.append({"vars":vars_list,"eq":eq,"removal_start":removal_start,"removal_end":removal_end})
                i = p
                continue
        i += 1
    used_names = set()
    for idx, tok in enumerate(tokens):
        if tok[0] != "ident":
            continue
        if idx in local_decl_indices or idx in param_indices:
            continue
        if idx > 0 and tokens[idx-1][0] == "keyword" and tokens[idx-1][1] == "function":
            continue
        used_names.add(tok[1])
    for stmt in local_stmts:
        names = [v["name"] for v in stmt["vars"] if v["name"] != "_"]
        all_unused = all(n not in used_names for n in names)
        if names and all_unused:
            edits.append((stmt["removal_start"], stmt["removal_end"], ""))
        else:
            for v in stmt["vars"]:
                nm = v["name"]
                if nm == "_":
                    continue
                if nm not in used_names:
                    edits.append((v["start"], v["end"], "_"))
    if not edits:
        return src, False
    edits.sort(key=lambda x: x[0], reverse=True)
    out = src
    for a,b,r in edits:
        out = out[:a] + r + out[b:]
    return out, True

def process_file(path, out_dir, dry_run, backup):
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    new_text, changed = transform_source(text)
    if not changed:
        return False
    dst = path
    if out_dir:
        _, tail = os.path.splitdrive(path)
        rel = tail.lstrip("\\/")
        dst = os.path.join(out_dir, rel)
    if dry_run:
        return True
    if backup and not out_dir:
        write_text(path + ".bak", text)
    write_text(dst, new_text)
    return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list-file", default=r"C:\Users\David\Desktop\glualint_unused_variables.txt")
    ap.add_argument("--output-dir", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--backup", action="store_true")
    args = ap.parse_args()
    files = parse_list_file(args.list_file)
    if not files:
        sys.stderr.write("No files to process\n")
        sys.exit(0)
    changed_any = False
    for fp in files:
        try:
            if os.path.isfile(fp):
                changed = process_file(fp, args.output_dir, args.dry_run, args.backup)
                changed_any = changed_any or changed
            else:
                sys.stderr.write(f"Missing file: {fp}\n")
        except Exception as e:
            sys.stderr.write(f"Error processing {fp}: {e}\n")
    if args.dry_run and changed_any:
        print("Changes would be made")
    sys.exit(0)

if __name__ == "__main__":
    main()
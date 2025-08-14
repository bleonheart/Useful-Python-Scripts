# Disclaimer

WIP, some may not work



# 🎮 Developer Utilities for Garry’s Mod

**A curated toolkit of Python scripts** to supercharge localization audits, asset management, Lua bundling, addon merging/splitting, and more!

---

## 🚀 Table of Contents

- [✨ Highlights](#-highlights)  
- [🛠️ Included Tools](#️-included-tools)  
  - [1. localization_usage_audit.py](#1-localization_usage_auditpy)  
  - [2. localization_analysis_report.py](#2-localization_analysis_reportpy)  
  - [3. generate_network_strings.py](#3-generate_network_stringspy)  
  - [4. hooks_discover_update_docs.py](#4-hooks_discover_update_docspy)  
  - [5. hooks_doc_usage_report.py](#5-hooks_doc_usage_reportpy)  
  - [6. extract_cdmaterials.py](#6-extract_cdmaterialspy)  
  - [7. gmod_asset_cleaner.py](#7-gmod_asset_cleanerpy)  
  - [8. lua_bundle.py](#8-lua_bundlepy)  
  - [9. lua_stack.py](#9-lua_stackpy)  
  - [10. addon_merge_and_split.py](#10-addon_merge_and_splitpy)  
  - [11. addon_merge_clean_split.py](#11-addon_merge_clean_splitpy)  
  - [12. lua_item_table_builder.py](#12-lua_item_table_builderpy)  
  - [13. privilege_report.py](#13-privilege_reportpy)  
  - [14. remove_duplicate_keys.py](#14-remove_duplicate_keyspy)  
  - [15. strip_sh_prefix.py](#15-strip_sh_prefixpy)

---

## ✨ Highlights

- 🎯 **Focused** on Garry’s Mod dev workflows  
- 🔍 **Automated** audits, clean-ups, merges & splits  
- 📦 **Modular** scripts—use only what you need  
- 📊 **JSON & reports** for easy integration  
- ⚡ **Zero dependencies** aside from `srctools` for some tools  

---

## 🛠️ Included Tools

---

### 1. `localization_usage_audit.py`

📝 **Audit localization usage**

- Extracts keys from a framework language file (e.g., `english.lua`)
- Scans for `L("KEY")` and `notifyLocalized("KEY")`
- Detects missing entries and placeholder mismatches (`%s`, `%d`)
- Writes JSON reports to Desktop: `argloc.json`, `loc_usage.json`, `loc_missing.json`, `loc_mismatch.json`

```bash
python files/localization_usage_audit.py
```

---

### 2. `localization_analysis_report.py`

📊 **Generate localization reports (framework + modules)**

- Produces Markdown or text reports per language
- Lists undefined calls, argument mismatches, unused keys
- Optionally cleans unused keys in-place

```bash
python files/localization_analysis_report.py --framework-gamemode-dir <path> --framework-languages-dir <path> --modules-root <path> --out-pattern localization_report_{name}.md --limit 500
```

---

### 3. `generate_network_strings.py`

🛰️ **Discover network strings and build a Lua registrar**

- Scans for `net.Start`, `net.Receive`, `util.AddNetworkString`, and Lilia big-table helpers
- Writes a Lua file that registers all unique network strings

```bash
python files/generate_network_strings.py <lua_root> <output_lua>
# Example
python files/generate_network_strings.py E:\GMOD\Server\garrysmod\gamemodes\Lilia\gamemode network_strings.lua
```

---

### 4. `hooks_discover_update_docs.py`

🔎 **Discover hooks and optionally update documentation**

- Scans Lua for `GM:Hook`, `MODULE:Hook`, `SCHEMA:Hook`, `hook.Add`, `hook.Run`
- Can write a `unique_hooks.txt`, a comparison list, and inject missing hooks into a docs file

```bash
python files/hooks_discover_update_docs.py
```

---

### 5. `hooks_doc_usage_report.py`

📘 **Compare documented hooks vs actual usage**

- Reads a Markdown file of documented hooks
- Scans a Lua tree for `hook.Run`/`hook.Call` producers and `hook.Add` consumers
- Outputs a Markdown report categorizing gaps

```bash
python files/hooks_doc_usage_report.py <docs_markdown> <code_root> <output_report>
```

---

### 6. `extract_cdmaterials.py`

🖼️ **Extract `cdmaterials` from models**

- Walks `.mdl` files recursively
- Uses `srctools` to parse `cdmaterials` paths
- Exports a JSON file of models and their material directories

```bash
pip install srctools
python files/extract_cdmaterials.py [models_root_folder] [output_file.json]
```

---

### 7. `gmod_asset_cleaner.py`

🧹 **Purge unused assets**

- Categorizes sounds, materials, models, particles, images
- Parses Lua to keep only referenced files
- Integrates `srctools` model scan for `cdmaterials`
- Optional deletions with space summaries

```bash
pip install srctools humanize
python files/gmod_asset_cleaner.py
```

---

### 8. `lua_bundle.py`

📦 **Bundle Lua files into one**

- Recursively collects `.lua` files
- Sorts and writes them with file headers

```bash
python files/lua_bundle.py <source_dir> <output_file>
```

---

### 9. `lua_stack.py`

🧾 **Simple Lua stacker (argparse variant)**

- Similar goal to `lua_bundle.py`, with `-s/--source` and `-o/--output` flags

```bash
python files/lua_stack.py -s <source_dir> -o <output.lua>
```

### 10. `addon_merge_and_split.py`

🔀 **Merge addon folders and split into packs**

- Merges directories and avoids duplicates
- Splits output into packs targeting ~1.9 GB

```bash
python files/addon_merge_and_split.py
```

### 11. `addon_merge_clean_split.py`

💥 **All-in-one merge + clean + split**

- Merges sources, flattens structure, scans Lua usage
- Cleans unused assets and writes summary lists
- Splits into packs and logs a space report

```bash
pip install srctools humanize
python files/addon_merge_clean_split.py
```

### 12. `lua_item_table_builder.py`

🧩 **Consolidate scattered `ITEM` fields into tables**

- Reads per-item `.lua` files and builds a consolidated Lua table per folder
- Configure `folder_table` paths at the top

```bash
python files/lua_item_table_builder.py
```

### 13. `privilege_report.py`

🔐 **Audit privileges (used vs. registered)**

- Scans framework and modules for privilege usage and registrations
- Merges JSON + Lua registrations and outputs Markdown report

```bash
python files/privilege_report.py
```

### 14. `remove_duplicate_keys.py`

🔍 **Remove duplicate key/value lines**

- Detects duplicate assignments and keeps the first occurrence

```bash
python files/remove_duplicate_keys.py
```

### 15. `strip_sh_prefix.py`

✂️ **Batch-rename Lua files**

- Recursively finds `sh_*.lua` and removes the `sh_` prefix

```bash
python files/strip_sh_prefix.py
```

---

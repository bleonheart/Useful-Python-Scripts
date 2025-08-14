# 🎮 Developer Utilities for Garry’s Mod

Python scripts to streamline localization audits, asset management, Lua bundling, and addon merging/splitting.

## Requirements

- Python 3.10+
- Optional: install extras when needed
  - `pip install srctools`
  - `pip install humanize`

## Configuring paths

Most scripts expose path defaults at the top of the file (e.g., `DEFAULT_LUA_ROOT`, `GMOD_DIR`, `ROOT`). Adjust those to your environment or pass CLI arguments when supported.

## Tool categories

### Localization
- `files/localization_usage_audit.py`: Scan for missing keys and placeholder mismatches.
```bash
python files/localization_usage_audit.py
```
- `files/localization_analysis_report.py`: Per-language report for framework + modules; can optionally clean unused keys.
```bash
python files/localization_analysis_report.py --framework-gamemode-dir <path> --framework-languages-dir <path> --modules-root <path> --out-pattern localization_report_{name}.md
```

### Hooks
- `files/hooks_discover_update_docs.py`: Discover hooks; optionally write `unique_hooks.txt`, comparison, and update docs.
```bash
python files/hooks_discover_update_docs.py
```
- `files/hooks_doc_usage_report.py`: Compare documented hooks vs actual usage and output a Markdown report.
```bash
python files/hooks_doc_usage_report.py <docs_markdown> <code_root> <output_report>
```

### Networking
- `files/generate_network_strings.py`: Find all network strings and emit a Lua registrar.
```bash
python files/generate_network_strings.py <lua_root> <output_lua>
```

### Assets
- `files/extract_cdmaterials.py`: Extract `cdmaterials` directories from `.mdl` files (srctools).
```bash
python files/extract_cdmaterials.py <models_root> <out.json>
```
- `files/gmod_asset_cleaner.py`: Find and optionally delete unused sounds/images/particles/models/materials.
```bash
python files/gmod_asset_cleaner.py
```
- `files/addon_merge_and_split.py`: Merge folders and split output into ~1.9 GB packs.
```bash
python files/addon_merge_and_split.py
```
- `files/addon_merge_clean_split.py`: Merge + clean unused assets + split packs, with reports.
```bash
python files/addon_merge_clean_split.py
```

### Lua utilities
- `files/lua_bundle.py`: Bundle all `.lua` files under a directory into one file.
```bash
python files/lua_bundle.py <source_dir> <output_file>
```
- `files/lua_stack.py`: Similar to bundle; flags `-s/--source` and `-o/--output`.
```bash
python files/lua_stack.py -s <source_dir> -o <output.lua>
```
- `files/lua_item_table_builder.py`: Build consolidated item tables from per-file `ITEM.*` definitions.
```bash
python files/lua_item_table_builder.py
```
- `files/strip_sh_prefix.py`: Remove the `sh_` prefix from `sh_*.lua` files.
```bash
python files/strip_sh_prefix.py
```

### Misc
- `files/privilege_report.py`: Report used vs registered privileges across framework and modules.
```bash
python files/privilege_report.py
```
- `files/remove_duplicate_keys.py`: Remove duplicate key/value lines, keeping the first occurrence.
```bash
python files/remove_duplicate_keys.py
```

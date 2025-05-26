# Disclaimer

WIP, some may not work



# 🎮 Developer Utilities for Garry’s Mod

**A curated toolkit of Python scripts** to supercharge localization audits, asset management, Lua bundling, addon merging/splitting, and more!

---

## 🚀 Table of Contents

- [✨ Highlights](#-highlights)  
- [🛠️ Included Tools](#️-included-tools)  
  - [1. localization_audit.py](#1-localization_auditpy)  
  - [2. strip_sh_prefix.py](#2-strip_sh_prefixpy)  
  - [3. remove_duplicates.py](#3-remove_duplicatespy)  
  - [4. cdmaterials_extractor.py](#4-cdmaterials_extractorpy)  
  - [5. gmod_asset_cleaner.py](#5-gmod_asset_cleanerpy)  
  - [6. lua_bundle.py](#6-lua_bundlepy)  
  - [7. addon_merger_splitter.py](#7-addon_merger_splitterpy)  
  - [8. lua_table_converter.py](#8-lua_table_converterpy)  
  - [9. super_addon_merger_splitter.py](#9-super_addon_merger_splitterpy)

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

### 1. `localization_audit.py`  
📝 **Audit your translations**  
- Extracts keys from `english.lua`  
- Scans for `L("KEY")` & `notifyLocalized("KEY")`  
- Finds missing entries & placeholder mismatches (`%s`, `%d`)  
- Outputs JSON reports:  
  - `argloc.json`  
  - `loc_usage.json`  
  - `loc_missing.json`  
  - `loc_mismatch.json`  

```bash
python localization_audit.py
````

---

### 2. `strip_sh_prefix.py`

✂️ **Batch-rename Lua files**

* Recursively finds `sh_*.lua`
* Renames to remove the `sh_` prefix
* Logs every operation

```bash
python strip_sh_prefix.py
```

---

### 3. `remove_duplicates.py`

🔍 **Clean duplicate key/value lines**

* Detects duplicates in Lua or config-like files
* Keeps the first occurrence, removes extras
* Detailed log of removals

```bash
python remove_duplicates.py
```

---

### 4. `cdmaterials_extractor.py`

🖼️ **Extract model materials**

* Walks `.mdl` files recursively
* Parses `cdmaterials` paths with `srctools`
* Outputs a tidy JSON report

```bash
pip install srctools
python cdmaterials_extractor.py [models_root_folder] [output_file.json]
```

---

### 5. `gmod_asset_cleaner.py`

🧹 **Purge unused assets**

* Categorizes sounds, materials, models, etc.
* Parses Lua to keep only referenced files
* Integrates `cdmaterials_extractor`
* Deletes leftovers & empty folders
* Generates disk-space & JSON summaries

```bash
pip install srctools
python gmod_asset_cleaner.py
```

---

### 6. `lua_bundle.py`

📦 **Merge Lua files**

* Recursively collects `.lua` files
* Sorts alphabetically with headers
* Outputs one combined, traceable file

```bash
python lua_bundle.py <source_dir> <output_file>
```

---

### 7. `addon_merger_splitter.py`

🔀 **Merge & chunk addons**

1. **Merge:** combines folders, dedupes, logs space saved
2. **Cleanup:** drops obsolete model formats
3. **Split:** creates ≤1.9 GB packs
4. **Logging:** real-time moves, deletions & errors

```bash
python addon_merger_splitter.py
```

---

### 8. `lua_table_converter.py`

🧩 **Convert scattered defs**

* Gathers `ITEM.<field> = …` entries
* Consolidates into clean Lua tables
* Outputs `sh_<folder>.lua` with readable formatting

```bash
python lua_table_converter.py
```

---

### 9. `super_addon_merger_splitter.py`

💥 **All-in-one merger + cleaner + splitter**

* Merges addons, dedupes & logs
* Cleans models & unused assets (`srctools` + `humanize`)
* Chunks into ≥1.9 GB packs
* Detailed space-saving reports

```bash
pip install srctools humanize
python super_addon_merger_splitter.py
```

---

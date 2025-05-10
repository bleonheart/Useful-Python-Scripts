## Localization Audit Tool (`localization_audit.py`)

**A script to audit your Garry’s Mod Lua translations for consistency.**

### Features

* **Defined Keys**
  Reads `english.lua` to list every `KEY = "…"` entry.
* **Placeholder Counts**
  Counts `%s` and `%d` slots in each translation string.
* **Usage Scan**
  Finds all calls of `L("KEY", …)` and `notifyLocalized("KEY", …)` across your codebase.
* **Missing Keys**
  Flags localization calls whose keys aren’t defined in `english.lua`.
* **Argument Mismatches**
  Detects when the number of arguments passed doesn’t match the string’s placeholders.
* **Reports**
  Saves JSON reports to your Desktop:

  * `argloc.json` (argument counts)
  * `loc_usage.json` (where keys are used)
  * `loc_missing.json` (undefined-key calls)
  * `loc_mismatch.json` (placeholder/argument mismatches)

### Usage

```bash
python localization_audit.py
```

---

## sh\_ Prefix Stripper (`strip_sh_prefix.py`)

**Batch-rename all Lua files beginning with `sh_`, removing that prefix and logging each result.**

### What It Does

1. Recursively searches a target directory for files matching `sh_*.lua`.
2. Renames each file by dropping the `sh_` prefix (e.g. `sh_item.lua` → `item.lua`).
3. Logs success or failure for every rename operation.

### Configuration

Edit the `root_dir` variable at the top of the script to point to your folder.

### Usage

```bash
python strip_sh_prefix.py
```

---

## Duplicate Key Remover (`remove_duplicates.py`)

**Removes duplicate `key = "value",` lines from a text file, keeping only the first occurrence.**

### Features

* Detects lines of the form `key = "value",` (including bracketed or quoted keys).
* Keeps the first definition of each key; removes subsequent duplicates.
* Writes the cleaned content to an output file.
* Logs every removed key to the console.

### Configuration

Adjust the constants at the top of the script:

```python
INPUT_PATH  = 'path/to/input_file.txt'
OUTPUT_PATH = 'path/to/output_file.txt'
```

### Usage

```bash
python remove_duplicates.py
```

---

## CDMaterials Extractor (`cdmaterials_extractor.py`)

**Scans `.mdl` model files for their `cdmaterials` paths and outputs a JSON report.**

### Features

* **Recursive Walk**
  Finds all `.mdl` files under a given root folder.
* **Model Parsing**
  Uses `srctools` to read each model’s `cdmaterials` list.
* **Error Resilience**
  Logs parse errors to stderr without halting the scan.
* **JSON Output**
  Writes an array of objects `{ "model": "...", "materials": [...] }` to a JSON file.

### Usage

```bash
python cdmaterials_extractor.py [models_root_folder] [output_file.json]
```

* `models_root_folder` (optional): directory to search (defaults to `~/Desktop/models`)
* `output_file.json` (optional): output path (defaults to `cdmaterials.json`)

---

## Garry’s Mod Asset Cleaner (`gmod_asset_cleaner.py`)

**Audit and clean unused assets in a Garry’s Mod addon folder.**

### Features

1. **Asset Discovery**
   Categorizes files into sounds (`.wav`, `.mp3`), particles (`.pcf`), images (`.png`, `.jpg`), materials (`.vmt`, `.vtf`), and models (`.mdl`, `.phy`).
2. **Usage Detection**
   Reads all Lua scripts to see which assets are actually referenced.
3. **Non-Material Cleanup**

   * Reports counts and sizes of unused sound/particle/image/model files.
   * Prompts to delete them and removes now-empty directories.
4. **Material Preservation**

   * Parses every model’s `cdmaterials` via `srctools` to keep required material folders.
   * Flags unused `.vmt`/`.vtf` files and optionally deletes them.
5. **Cleanup Summary**

   * Cleans up empty folders.
   * Reports total freed disk space.
6. **JSON Report**
   Exports `cdmaterials.json` containing each model’s material paths.

### Usage

```bash
python gmod_asset_cleaner.py
```

---

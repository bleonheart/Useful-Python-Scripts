# Developer Utilities – Python Script Collection

A collection of Python scripts to assist Garry’s Mod developers with localization auditing, asset management, Lua file organization, and more. These tools are designed to make your workflow cleaner, faster, and less error-prone.

## 📦 Included Tools

### `localization_audit.py`
**Audit your Garry’s Mod Lua translations for consistency.**

- Extracts all defined keys from `english.lua`.
- Scans your codebase for usage of `L("KEY")` and `notifyLocalized("KEY")`.
- Detects missing keys, mismatches in placeholder arguments (`%s`, `%d`), and generates detailed JSON reports.
- **Output files** (saved to your Desktop):
  - `argloc.json`
  - `loc_usage.json`
  - `loc_missing.json`
  - `loc_mismatch.json`

#### Usage
```bash
python localization_audit.py
````

---

### `strip_sh_prefix.py`

**Batch-rename Lua files by removing the `sh_` prefix.**

* Recursively renames files like `sh_example.lua` → `example.lua`.
* Logs all renames.

#### Configuration

Edit the `root_dir` variable at the top of the script.

#### Usage

```bash
python strip_sh_prefix.py
```

---

### `remove_duplicates.py`

**Remove duplicate key-value lines in Lua or config-like files.**

* Detects `key = "value",` lines.
* Keeps the first occurrence, removes the rest.
* Logs each removed duplicate.

#### Configuration

```python
INPUT_PATH  = 'path/to/input_file.txt'
OUTPUT_PATH = 'path/to/output_file.txt'
```

#### Usage

```bash
python remove_duplicates.py
```

---

### `cdmaterials_extractor.py`

**Extract all `cdmaterials` paths from `.mdl` files.**

* Recursively walks a directory of models.
* Uses [`srctools`](https://github.com/sgb-io/srctools) to parse material paths.
* Generates a clean JSON report.
* 
## 🛠 Requirements

```bash
pip install srctools
```

#### Usage

```bash
python cdmaterials_extractor.py [models_root_folder] [output_file.json]
```

* `models_root_folder`: (Optional) Defaults to `~/Desktop/models`
* `output_file.json`: (Optional) Defaults to `cdmaterials.json`

---

### `gmod_asset_cleaner.py`

**Scan a Garry’s Mod addon for unused assets and clean them.**

* Categorizes assets: sounds, particles, images, materials, models.
* Scans Lua files for actual usage.
* Handles `cdmaterials` parsing to preserve used materials.
* Cleans up unused files and empty folders.
* Generates disk space usage summary and a JSON report.
* 
## 🛠 Requirements

```bash
pip install srctools
```

#### Usage

```bash
python gmod_asset_cleaner.py
```

---

### `lua_bundle.py`

**Bundle all Lua files from a directory into a single file.**

* Recursively collects and alphabetically stacks `.lua` files.
* Adds headers for traceability.
* Outputs a single, clean file.

#### Usage

```bash
python stack_lua_files.py <source_dir> <output_file>
```

---

## Addon Merger & Splitter (`addon_merger_splitter.py`)

**Consolidates multiple Garry’s Mod addon folders, removes duplicates, strips unused model formats, and splits into pack-sized chunks.**

### Features

1. **Merge Operation**

   * Combines all subfolders in a source directory into a single destination.
   * Skips duplicates and logs how much space is saved.
   * Deletes empty source folders after moving.

2. **Format Cleanup**

   * Removes obsolete or platform-specific model files: `.dx80.vtx`, `.xbox.vtx`, `.sw.vtx`, `.360.vtx`.
   * Reports count and total space freed for each removed format.

3. **Pack Splitting**

   * Organizes all files in the destination directory into numbered subfolders.
   * Ensures no single pack exceeds 1.9 GB, suitable for workshop uploads.

4. **Logging**

   * Provides real-time logging of file operations, errors, and summaries.

### Usage

```bash
python addon_merger_splitter.py
```

---

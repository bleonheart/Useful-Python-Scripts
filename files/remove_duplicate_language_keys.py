import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Hard-coded paths - modify these as needed
FRAMEWORK_DIR = r"D:\Lilia\gamemode"  # Path to framework directory (e.g., gamemode)
MODULES_DIR = r"D:\Lilia\gamemode\modules"     # Path to modules directory
LANGUAGES = ["english", "french", "german", "portuguese", "spanish"]  # Languages to process
APPLY_CHANGES = True                       # Set to True to actually remove keys (False = dry run)
REPORT_FILE = None                          # Set to file path to save report, or None to skip

class LanguageKeyCleaner:
    def __init__(self, framework_dir: str, modules_dir: str = None):
        self.framework_dir = Path(framework_dir)
        self.modules_dir = Path(modules_dir) if modules_dir else None
        self.duplicate_keys: Dict[str, List[Tuple[str, str, str, str]]] = {}  # language -> list of (file_path, key, value, line_number)
        
    def scan_for_duplicates_in_file(self, file_path: Path, language: str) -> None:
        """Scan a single language file for duplicate keys within the same file."""
        if not file_path.exists():
            return

        print(f"Scanning for duplicates in: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()

        # Parse keys with line numbers
        key_to_lines = {}  # key -> list of line numbers and values
        for line_num, line in enumerate(lines, 1):
            # Match pattern: KEY = "VALUE"
            match = re.match(r'^\s*(\w+)\s*=\s*"([^"]*)"', line.strip())
            if match:
                key, value = match.groups()
                if key not in key_to_lines:
                    key_to_lines[key] = []
                key_to_lines[key].append((line_num, value, line))

        # Find duplicates (keys that appear more than once)
        duplicates_found = 0
        for key, occurrences in key_to_lines.items():
            if len(occurrences) > 1:
                # Keep the first occurrence, mark others as duplicates
                first_occurrence = occurrences[0]
                for occurrence in occurrences[1:]:
                    line_num, value, line_content = occurrence
                    self.duplicate_keys[language].append((str(file_path), key, value, str(line_num)))
                    duplicates_found += 1
                    print(f"  Found duplicate: {key} = '{value}' at line {line_num}")

        if duplicates_found == 0:
            print(f"  No duplicates found in {file_path}")

    def scan_language_files(self, language: str) -> None:
        """Scan all language files for a specific language."""
        print(f"\n{'='*50}")
        print(f"Processing language: {language}")
        print(f"{'='*50}")

        # Initialize duplicate keys list for this language
        if language not in self.duplicate_keys:
            self.duplicate_keys[language] = []

        # Scan framework language file
        framework_file = self.framework_dir / "languages" / f"{language}.lua"
        self.scan_for_duplicates_in_file(framework_file, language)

        # Scan module language files
        if self.modules_dir and self.modules_dir.exists():
            for module_dir in self.modules_dir.iterdir():
                if not module_dir.is_dir():
                    continue

                lang_file = module_dir / "languages" / f"{language}.lua"
                self.scan_for_duplicates_in_file(lang_file, language)

    def remove_duplicate_keys(self, dry_run: bool = True) -> None:
        """Remove duplicate keys from language files."""
        total_duplicates = sum(len(duplicates) for duplicates in self.duplicate_keys.values())

        if total_duplicates == 0:
            print("No duplicate keys found to remove")
            return

        print(f"\nFound {total_duplicates} duplicate keys to remove across all languages:")
        for language, duplicates in self.duplicate_keys.items():
            if duplicates:
                print(f"\n{language.upper()} ({len(duplicates)} duplicates):")
                for file_path, key, value, line_num in duplicates:
                    print(f"  {file_path}: line {line_num}: {key} = '{value}'")

        if dry_run:
            print("\nDRY RUN - No files will be modified")
            print("Use --apply to actually remove the keys")
            return

        # Group duplicates by file path for processing
        files_to_process = {}
        for language, duplicates in self.duplicate_keys.items():
            for file_path, key, value, line_num in duplicates:
                if file_path not in files_to_process:
                    files_to_process[file_path] = []
                files_to_process[file_path].append((language, key, line_num))

        # Process each file
        for file_path, duplicates in files_to_process.items():
            self._remove_duplicates_from_file(file_path, duplicates)

    def _remove_duplicates_from_file(self, file_path: str, duplicates: List[Tuple[str, str, str]]) -> None:
        """Remove duplicate keys from a specific file."""
        file_path = Path(file_path)
        if not file_path.exists():
            print(f"File not found: {file_path}")
            return

        # Read current content
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()

        original_lines = lines.copy()
        lines_to_remove = set()

        # Collect line numbers to remove (skip the first occurrence of each key)
        for language, key, line_num in duplicates:
            lines_to_remove.add(int(line_num))

        # Remove lines (in reverse order to maintain correct indices)
        for line_num in sorted(lines_to_remove, reverse=True):
            if 1 <= line_num <= len(lines):
                lines.pop(line_num - 1)  # Convert to 0-based index

        # Check if any changes were made
        if lines != original_lines:
            # Create backup
            backup_file = file_path.with_suffix('.lua.bak')
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(original_lines) + '\n')

            # Write updated content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines) + '\n')

            print(f"Updated {file_path} (backup: {backup_file})")
            print(f"  Removed {len(lines_to_remove)} duplicate lines")
        else:
            print(f"No changes made to {file_path}")

    def generate_report(self) -> str:
        """Generate a report of duplicate keys found."""
        total_duplicates = sum(len(duplicates) for duplicates in self.duplicate_keys.values())

        if total_duplicates == 0:
            return "No duplicate keys found."

        report = f"# Duplicate Language Keys Report\n\n"
        report += f"Found {total_duplicates} duplicate keys across {len([lang for lang, duplicates in self.duplicate_keys.items() if duplicates])} languages.\n"
        report += "These are keys that appear multiple times within the same language file.\n\n"

        # Group by language
        for language, duplicates in self.duplicate_keys.items():
            if not duplicates:
                continue

            report += f"## {language.upper()}\n\n"
            report += f"Found {len(duplicates)} duplicate keys in {language}:\n\n"

            # Group by file
            files = {}
            for file_path, key, value, line_num in duplicates:
                if file_path not in files:
                    files[file_path] = []
                files[file_path].append((key, value, line_num))

            for file_path, keys in files.items():
                report += f"### {Path(file_path).name}\n\n"
                report += "| Key | Value | Line Number |\n"
                report += "|-----|-------|-------------|\n"

                for key, value, line_num in keys:
                    report += f"| `{key}` | `{value}` | {line_num} |\n"

                report += "\n"

        return report

def main():
    # Use hard-coded paths and settings
    print(f"Framework directory: {FRAMEWORK_DIR}")
    print(f"Modules directory: {MODULES_DIR}")
    print(f"Languages: {', '.join(LANGUAGES)}")
    print(f"Apply changes: {APPLY_CHANGES}")
    print(f"Report file: {REPORT_FILE}")
    print("-" * 50)

    # Initialize cleaner
    cleaner = LanguageKeyCleaner(FRAMEWORK_DIR, MODULES_DIR)

    # Process each language
    for language in LANGUAGES:
        cleaner.scan_language_files(language)

    # Generate report for all languages
    report = cleaner.generate_report()
    print("\n" + "="*50)
    print("SUMMARY REPORT")
    print("="*50)
    print(report)

    # Save report if requested
    if REPORT_FILE:
        with open(REPORT_FILE, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"Report saved to: {REPORT_FILE}")

    # Remove duplicates from all languages
    cleaner.remove_duplicate_keys(dry_run=not APPLY_CHANGES)

if __name__ == "__main__":
    main()

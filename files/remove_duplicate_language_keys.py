import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Hard-coded paths - modify these as needed
FRAMEWORK_DIR = r"E:\GMOD\Server\garrysmod\gamemodes\Lilia"  # Path to framework directory (e.g., gamemode)
MODULES_DIR = r"E:\GMOD\Server\garrysmod\gamemodes\metro\gitmodules"     # Path to modules directory
LANGUAGE = "english"                        # Language to process
APPLY_CHANGES = False                       # Set to True to actually remove keys (False = dry run)
REPORT_FILE = None                          # Set to file path to save report, or None to skip

class LanguageKeyCleaner:
    def __init__(self, framework_dir: str, modules_dir: str = None):
        self.framework_dir = Path(framework_dir)
        self.modules_dir = Path(modules_dir) if modules_dir else None
        self.framework_keys: Dict[str, str] = {}
        self.duplicate_keys: List[Tuple[str, str, str]] = []
        
    def load_framework_keys(self, language: str = "english") -> None:
        """Load all language keys from the main framework language file."""
        framework_lang_file = self.framework_dir / "languages" / f"{language}.lua"
        
        if not framework_lang_file.exists():
            print(f"Framework language file not found: {framework_lang_file}")
            return
            
        print(f"Loading framework keys from: {framework_lang_file}")
        
        with open(framework_lang_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Parse LANGUAGE table
        pattern = r'(\w+)\s*=\s*"([^"]*)"'
        matches = re.findall(pattern, content)
        
        for key, value in matches:
            self.framework_keys[key] = value
            
        print(f"Loaded {len(self.framework_keys)} framework keys")
        
    def scan_modules_for_duplicates(self, language: str = "english") -> None:
        """Scan module directories for duplicate language keys."""
        if not self.modules_dir or not self.modules_dir.exists():
            print("No modules directory specified or found")
            return
            
        print(f"Scanning modules directory: {self.modules_dir}")
        
        for module_dir in self.modules_dir.iterdir():
            if not module_dir.is_dir():
                continue
                
            lang_file = module_dir / "languages" / f"{language}.lua"
            if not lang_file.exists():
                continue
                
            print(f"Checking module: {module_dir.name}")
            self._check_module_language_file(lang_file, module_dir.name)
            
    def _check_module_language_file(self, lang_file: Path, module_name: str) -> None:
        """Check a single module language file for duplicate keys."""
        with open(lang_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Parse LANGUAGE table
        pattern = r'(\w+)\s*=\s*"([^"]*)"'
        matches = re.findall(pattern, content)
        
        for key, value in matches:
            if key in self.framework_keys:
                framework_value = self.framework_keys[key]
                if value == framework_value:
                    self.duplicate_keys.append((module_name, key, value))
                    print(f"  Found duplicate key: {key} = '{value}'")
                else:
                    print(f"  Found conflicting key: {key} = '{value}' (framework: '{framework_value}')")
                    
    def remove_duplicate_keys(self, dry_run: bool = True) -> None:
        """Remove duplicate keys from module language files."""
        if not self.duplicate_keys:
            print("No duplicate keys found to remove")
            return
            
        print(f"\nFound {len(self.duplicate_keys)} duplicate keys to remove:")
        for module, key, value in self.duplicate_keys:
            print(f"  {module}: {key} = '{value}'")
            
        if dry_run:
            print("\nDRY RUN - No files will be modified")
            print("Use --apply to actually remove the keys")
            return
            
        # Group by module for processing
        modules_to_process = {}
        for module, key, value in self.duplicate_keys:
            if module not in modules_to_process:
                modules_to_process[module] = []
            modules_to_process[module].append(key)
            
        for module_name, keys_to_remove in modules_to_process.items():
            self._remove_keys_from_module(module_name, keys_to_remove)
            
    def _remove_keys_from_module(self, module_name: str, keys_to_remove: List[str]) -> None:
        """Remove specific keys from a module's language file."""
        if not self.modules_dir:
            return
            
        lang_file = self.modules_dir / module_name / "languages" / "english.lua"
        if not lang_file.exists():
            print(f"Language file not found for module {module_name}")
            return
            
        # Read current content
        with open(lang_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Remove each key
        original_content = content
        for key in keys_to_remove:
            # Pattern to match the entire key-value line
            pattern = rf'^\s*{re.escape(key)}\s*=\s*"[^"]*",?\s*$'
            content = re.sub(pattern, '', content, flags=re.MULTILINE)
            
        # Clean up empty lines
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        
        if content != original_content:
            # Create backup
            backup_file = lang_file.with_suffix('.lua.bak')
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(original_content)
                
            # Write updated content
            with open(lang_file, 'w', encoding='utf-8') as f:
                f.write(content)
                
            print(f"Updated {lang_file} (backup: {backup_file})")
        else:
            print(f"No changes made to {lang_file}")
            
    def generate_report(self) -> str:
        """Generate a report of duplicate keys found."""
        if not self.duplicate_keys:
            return "No duplicate keys found."
            
        report = f"# Duplicate Language Keys Report\n\n"
        report += f"Found {len(self.duplicate_keys)} duplicate keys across modules:\n\n"
        
        # Group by module
        modules = {}
        for module, key, value in self.duplicate_keys:
            if module not in modules:
                modules[module] = []
            modules[module].append((key, value))
            
        for module_name, keys in modules.items():
            report += f"## {module_name}\n\n"
            report += "| Key | Value | Framework Value |\n"
            report += "|-----|-------|----------------|\n"
            
            for key, value in keys:
                framework_value = self.framework_keys.get(key, "N/A")
                report += f"| `{key}` | `{value}` | `{framework_value}` |\n"
                
            report += "\n"
            
        return report

def main():
    # Use hard-coded paths and settings
    print(f"Framework directory: {FRAMEWORK_DIR}")
    print(f"Modules directory: {MODULES_DIR}")
    print(f"Language: {LANGUAGE}")
    print(f"Apply changes: {APPLY_CHANGES}")
    print(f"Report file: {REPORT_FILE}")
    print("-" * 50)
    
    # Initialize cleaner
    cleaner = LanguageKeyCleaner(FRAMEWORK_DIR, MODULES_DIR)
    
    # Load framework keys
    cleaner.load_framework_keys(LANGUAGE)
    
    # Scan for duplicates
    cleaner.scan_modules_for_duplicates(LANGUAGE)
    
    # Generate report
    report = cleaner.generate_report()
    print(report)
    
    # Save report if requested
    if REPORT_FILE:
        with open(REPORT_FILE, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"Report saved to: {REPORT_FILE}")
    
    # Remove duplicates
    cleaner.remove_duplicate_keys(dry_run=not APPLY_CHANGES)

if __name__ == "__main__":
    main()

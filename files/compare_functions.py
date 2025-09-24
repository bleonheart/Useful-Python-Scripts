#!/usr/bin/env python3
"""
Function comparison module for analyzing Lua function documentation coverage.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass


@dataclass
class FunctionInfo:
    """Information about a function"""
    name: str
    line_number: int
    is_server_only: bool = False
    is_client_only: bool = False
    parameters: List[str] = None
    description: str = ""

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = []


class LuaFunctionExtractor:
    """Extracts functions from Lua files"""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)

    def extract_functions_from_file(self, file_path: str) -> Dict[str, FunctionInfo]:
        """Extract all functions from a single Lua file"""
        functions = {}

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}")
            return functions

        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            func_name = None
            params = ""
            
            # Check for function lia.xxxxx.xxxx(...) pattern - ONLY lia functions
            match1 = re.search(r'^\s*function\s+(lia\.[A-Za-z_][\w\.]*)\s*\(([^)]*)\)', line)
            if match1:
                func_name = match1.group(1)
                params = match1.group(2)
            else:
                # Check for lia.xxxxx.xxxx = function(...) pattern - ONLY lia functions
                match2 = re.search(r'^\s*(lia\.[A-Za-z_][\w\.]*)\s*=\s*function\s*\(([^)]*)\)', line)
                if match2:
                    func_name = match2.group(1)
                    params = match2.group(2)
                else:
                    # Check for meta function pattern: function metaTable:functionName(...)
                    # Only detect meta functions that end with "Meta" (e.g., characterMeta, itemMeta, etc.)
                    match3 = re.search(r'^\s*function\s+([A-Za-z_]*Meta):([A-Za-z_][\w]*)\s*\(([^)]*)\)', line)
                    if match3:
                        meta_table = match3.group(1)
                        method_name = match3.group(2)
                        params = match3.group(3)
                        # Keep meta table type to distinguish same method names across different metas
                        func_name = f"{meta_table}:{method_name}"
                    else:
                        continue  # Skip if no pattern matched

            if func_name:
                # Parse parameters
                param_list = []
                if params and params.strip():
                    param_list = [p.strip() for p in params.split(',') if p.strip()]

                # Determine realm (server/client/shared)
                is_server = self._is_server_realm(content, line_num)
                is_client = self._is_client_realm(content, line_num)

                functions[func_name] = FunctionInfo(
                    name=func_name,
                    line_number=line_num,
                    is_server_only=is_server and not is_client,
                    is_client_only=is_client and not is_server,
                    parameters=param_list
                )

        return functions

    def _is_server_realm(self, content: str, line_num: int) -> bool:
        """Check if function is in server realm"""
        lines = content.split('\n')
        start_line = max(0, line_num - 20)  # Look 20 lines back

        for i in range(start_line, line_num):
            line = lines[i].strip().lower()
            if 'if server' in line or 'if (server)' in line:
                return True
            if 'if client' in line or 'if (client)' in line:
                return False
            if 'server' in line and ('then' in line or '{' in line):
                return True

        return False

    def _is_client_realm(self, content: str, line_num: int) -> bool:
        """Check if function is in client realm"""
        lines = content.split('\n')
        start_line = max(0, line_num - 20)  # Look 20 lines back

        for i in range(start_line, line_num):
            line = lines[i].strip().lower()
            if 'if client' in line or 'if (client)' in line:
                return True
            if 'if server' in line or 'if (server)' in line:
                return False
            if 'client' in line and ('then' in line or '{' in line):
                return True

        return False

    def extract_all_functions(self) -> Dict[str, Dict[str, FunctionInfo]]:
        """Extract functions from all Lua files in the gamemode"""
        all_functions = {}

        # Scan all .lua files
        for root, dirs, files in os.walk(self.base_path):
            # Skip certain directories
            dirs[:] = [d for d in dirs if d not in ['node_modules', '.git']]

            for file in files:
                if file.endswith('.lua'):
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, self.base_path)

                    functions = self.extract_functions_from_file(file_path)
                    if functions:
                        all_functions[relative_path] = functions

        return all_functions


class DocumentationParser:
    """Parses documentation files to extract documented functions"""

    def __init__(self, docs_path: str):
        self.docs_path = Path(docs_path)

    def extract_documented_functions(self) -> Dict[str, Dict[str, FunctionInfo]]:
        """Extract all documented functions from documentation files"""
        documented_functions = {}

        # Look for library documentation files
        libraries_path = self.docs_path / "docs" / "libraries"
        if libraries_path.exists():
            for md_file in libraries_path.glob("*.md"):
                if md_file.name.startswith("lia."):
                    functions = self._parse_library_file(md_file)
                    if functions:
                        documented_functions[md_file.name] = functions

        # Look for meta documentation files
        meta_path = self.docs_path / "docs" / "meta"
        if meta_path.exists():
            for md_file in meta_path.glob("*.md"):
                functions = self._parse_meta_file(md_file)
                if functions:
                    documented_functions[f"meta/{md_file.name}"] = functions

        return documented_functions

    def _parse_library_file(self, file_path: Path) -> Dict[str, FunctionInfo]:
        """Parse a library documentation file"""
        functions = {}

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}")
            return functions

        lines = content.split('\n')

        # Determine library name: prefer content backticked name (e.g., (`lia.administrator`)); fallback to filename stem
        library_name = file_path.stem
        try:
            # Capture `lia` or dotted forms like `lia.util`, `lia.administrator`
            m = re.search(r"\(`(lia(?:\.[\w\.]+)?)`\)", content)
            if m:
                library_name = m.group(1)
        except Exception:
            pass

        # Look for function headers in the format "### functionName" or "### lia.util.functionName"
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()

            # Look for function headers like "### lia.include"
            func_match = re.search(r'^###+\s+([A-Za-z_][\w\.]*)\s*$', stripped)
            if func_match:
                header_name = func_match.group(1)
                # If header already includes dots (fully qualified), keep it; otherwise qualify with library name
                if '.' in header_name:
                    qualified_name = header_name
                else:
                    qualified_name = f"{library_name}.{header_name}"
                # Extract parameters from the following lines
                params = self._extract_parameters_from_docs(lines, line_num)

                functions[qualified_name] = FunctionInfo(
                    name=qualified_name,
                    line_number=line_num,
                    parameters=params
                )

        return functions

    def _extract_parameters_from_docs(self, lines: List[str], start_line: int) -> List[str]:
        """Extract parameters from documentation following a function header"""
        params = []

        # Look for the Parameters section
        in_params_section = False
        for i in range(start_line, min(start_line + 50, len(lines))):  # Look up to 50 lines ahead
            line = lines[i].strip()

            if line.lower() == '**parameters**':
                in_params_section = True
                continue
            elif line.startswith('**') and in_params_section:
                # We've moved to the next section
                break
            elif in_params_section and line.startswith('* `'):
                # Extract parameter name from format: * `param` (*type*): description
                param_match = re.search(r'\* `([^`]+)`', line)
                if param_match:
                    params.append(param_match.group(1))

        return params

    def _parse_meta_file(self, file_path: Path) -> Dict[str, FunctionInfo]:
        """Parse a meta documentation file"""
        functions = {}

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}")
            return functions

        lines = content.split('\n')
        # Derive meta table name from file name with overrides
        # Default: <stem>Meta (e.g., character.md -> characterMeta)
        stem = file_path.stem
        overrides = {
            'tool': 'toolGunMeta',
        }
        meta_table = overrides.get(stem, f"{stem}Meta")

        # Look for method definitions in two formats:
        # 1. ### methodName (standard meta documentation format)
        # 2. `object:method(param)` (inline code format)
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Look for method headers like "### methodName"
            method_match = re.search(r'^###+\s+([A-Za-z_][\w]*)\s*$', stripped)
            if method_match:
                method_name = method_match.group(1)
                # Extract parameters from the following lines
                params = self._extract_parameters_from_docs(lines, line_num)

                # Store type-qualified meta name to avoid cross-type overrides
                qualified_name = f"{meta_table}:{method_name}"
                functions[qualified_name] = FunctionInfo(
                    name=qualified_name,
                    line_number=line_num,
                    parameters=params
                )
            else:
                # Look for method signatures like: `object:method(param)`
                method_match = re.search(r'`([A-Za-z_][\w\.:]*)\(([^)]*)\)`', line)
                if method_match:
                    method_name = method_match.group(1)
                    params_str = method_match.group(2)
                    params = [p.strip() for p in params_str.split(',') if p.strip()]

                    # If inline format includes object:method, keep as-is; otherwise, qualify
                    if ':' in method_name and method_name.split(':', 1)[0].endswith('Meta'):
                        qualified_name = method_name
                    else:
                        qualified_name = f"{meta_table}:{method_name}"

                    functions[qualified_name] = FunctionInfo(
                        name=qualified_name,
                        line_number=line_num,
                        parameters=params
                    )

        return functions


class FunctionComparator:
    """Compares functions between code and documentation"""

    def __init__(self, base_path: str, docs_path: str = None):
        self.base_path = Path(base_path)
        self.docs_path = Path(docs_path) if docs_path else self.base_path.parent / "documentation"

        self.extractor = LuaFunctionExtractor(str(self.base_path))
        self.parser = DocumentationParser(str(self.docs_path))

    def compare_functions(self) -> Dict[str, Dict]:
        """Compare functions between code and documentation"""
        print("Extracting functions from code...")
        code_functions = self.extractor.extract_all_functions()

        print("Extracting functions from documentation...")
        doc_functions = self.parser.extract_documented_functions()

        print("Comparing functions...")
        comparison_results = {}

        # Flatten all code functions for global comparison
        all_code_functions = set()
        for file_functions in code_functions.values():
            all_code_functions.update(file_functions.keys())

        # Flatten all documented functions
        all_documented_functions = set()
        for doc_file_functions in doc_functions.values():
            all_documented_functions.update(doc_file_functions.keys())

        # Find truly extra documented functions (documented but don't exist in any code file)
        # Filter out global functions that are not expected to follow library naming patterns
        excluded_functions = {'L'}  # Global localization function
        filtered_documented = {func for func in all_documented_functions if func not in excluded_functions}
        extra_documented = sorted(filtered_documented - all_code_functions)

        # Compare each code file with documentation
        for file_path, functions in code_functions.items():
            file_comparison = self._compare_file_functions(file_path, functions, doc_functions)
            if file_comparison:
                comparison_results[file_path] = file_comparison

        # Add global extra documented functions to the first file's results for reporting
        if comparison_results and extra_documented:
            first_file = next(iter(comparison_results.keys()))
            comparison_results[first_file]['extra_documented'] = extra_documented
            comparison_results[first_file]['extra_documented_count'] = len(extra_documented)

        return comparison_results

    def _extract_base_function_name(self, full_name: str) -> str:
        """Extract base function name from dotted name (e.g., 'lia.administrator.hasAccess' -> 'hasAccess')"""
        if '.' in full_name:
            return full_name.split('.')[-1]
        return full_name

    def _compare_file_functions(self, file_path: str, code_functions: Dict[str, FunctionInfo],
                               doc_functions: Dict[str, Dict[str, FunctionInfo]]) -> Dict:
        """Compare functions for a single file"""
        # Flatten all documented functions
        all_documented = {}
        for doc_file, funcs in doc_functions.items():
            for func_name, func_info in funcs.items():
                all_documented[func_name] = func_info

        # Find functions in this file that are documented
        documented_in_file = {}
        missing_functions = []

        for func_name, func_info in code_functions.items():
            # Check if function is documented
            is_documented = False
            
            # First check if the full function name is documented
            if func_name in all_documented:
                is_documented = True
            else:
                # For meta functions, require exact type-qualified match (e.g., characterMeta:tostring)
                if ':' in func_name and func_name.split(':', 1)[0].endswith('Meta'):
                    if func_name in all_documented:
                        is_documented = True
                else:
                    # For lia.xxxxx functions, extract base function name and check
                    if func_name.startswith('lia.'):
                        # Require either fully qualified or base-name match present in docs
                        if func_name in all_documented:
                            is_documented = True
                        else:
                            base_name = self._extract_base_function_name(func_name)
                            if base_name in all_documented:
                                is_documented = True
            
            if is_documented:
                documented_in_file[func_name] = func_info
            else:
                missing_functions.append(func_name)

        # Don't list "extra documented" functions per-file - this causes false positives
        # Instead, we'll handle this globally in the main comparison method
        extra_documented = []

        # Create unique lists for missing and extra functions
        unique_missing = sorted(set(missing_functions))
        unique_extra = sorted(set(extra_documented))

        return {
            'total_functions': len(code_functions),
            'documented_functions': len(documented_in_file),
            'missing_functions': unique_missing,
            'extra_documented': unique_extra,
            'functions': {name: {
                'line_number': info.line_number,
                'is_server_only': info.is_server_only,
                'is_client_only': info.is_client_only,
                'parameters': info.parameters
            } for name, info in code_functions.items()},
            # Keep original counts for detailed analysis
            'missing_functions_count': len(missing_functions),
            'extra_documented_count': len(extra_documented)
        }

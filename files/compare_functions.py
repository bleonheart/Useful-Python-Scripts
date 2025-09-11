import os
import re
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class FunctionInfo:
    """Represents a function found in Lua code"""
    name: str
    file_path: str
    line_number: int
    is_meta: bool
    is_server_only: bool = False
    is_client_only: bool = False
    parameters: List[str] = None
    return_type: str = None

@dataclass
class DocumentationInfo:
    """Represents documentation for a function"""
    name: str
    file_path: str
    has_purpose: bool = False
    has_parameters: bool = False
    has_returns: bool = False
    has_realm: bool = False
    has_example: bool = False

class LuaFunctionExtractor:
    """Extracts function definitions from Lua files"""
    
    def __init__(self):
        self.functions = []
        self.function_patterns = [
            # Standard function definitions
            r'function\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(',
            # Method definitions (self:method)
            r'function\s+([a-zA-Z_][a-zA-Z0-9_]*):([a-zA-Z_][a-zA-Z0-9_]*)\s*\(',
            # Table method definitions
            r'([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*function\s*\(',
            # Local function definitions
            r'local\s+function\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(',
        ]
        
    def extract_functions_from_file(self, file_path: str, is_meta: bool = False) -> List[FunctionInfo]:
        """Extract all function definitions from a Lua file"""
        functions = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # Check for SERVER/CLIENT blocks
                is_server_only = False
                is_client_only = False
                
                # Look for function definitions
                for pattern in self.function_patterns:
                    matches = re.finditer(pattern, line)
                    for match in matches:
                        if len(match.groups()) == 1:
                            # Standard function
                            func_name = match.group(1)
                        else:
                            # Method definition
                            func_name = f"{match.group(1)}:{match.group(2)}"
                        
                        # Check if this is in a SERVER/CLIENT block
                        context_lines = lines[max(0, line_num-10):line_num]
                        for context_line in reversed(context_lines):
                            if 'if SERVER then' in context_line:
                                is_server_only = True
                                break
                            elif 'if CLIENT then' in context_line:
                                is_client_only = True
                                break
                            elif 'end' in context_line and (is_server_only or is_client_only):
                                break
                        
                        # Extract parameters if possible
                        param_match = re.search(r'\(([^)]*)\)', line)
                        parameters = []
                        if param_match:
                            param_str = param_match.group(1).strip()
                            if param_str:
                                parameters = [p.strip() for p in param_str.split(',')]
                        
                        functions.append(FunctionInfo(
                            name=func_name,
                            file_path=file_path,
                            line_number=line_num,
                            is_meta=is_meta,
                            is_server_only=is_server_only,
                            is_client_only=is_client_only,
                            parameters=parameters
                        ))
                        
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            
        return functions

class DocumentationParser:
    """Parses documentation files to extract function information"""
    
    def __init__(self):
        self.documented_functions = {}
        
    def parse_documentation_file(self, file_path: str) -> Dict[str, DocumentationInfo]:
        """Parse a documentation file and extract function information"""
        functions = {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Split content into sections
            sections = re.split(r'^###\s+', content, flags=re.MULTILINE)
            
            for section in sections[1:]:  # Skip first empty section
                lines = section.split('\n')
                if not lines:
                    continue
                    
                # Extract function name from first line
                func_name = lines[0].strip()
                if not func_name:
                    continue
                
                # Check for documentation elements
                has_purpose = any('**Purpose**' in line for line in lines)
                has_parameters = any('**Parameters**' in line for line in lines)
                has_returns = any('**Returns**' in line for line in lines)
                has_realm = any('**Realm**' in line for line in lines)
                has_example = any('**Example Usage**' in line for line in lines)
                
                functions[func_name] = DocumentationInfo(
                    name=func_name,
                    file_path=file_path,
                    has_purpose=has_purpose,
                    has_parameters=has_parameters,
                    has_returns=has_returns,
                    has_realm=has_realm,
                    has_example=has_example
                )
                
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            
        return functions

class FunctionComparator:
    """Compares functions between original files and documentation"""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.lua_extractor = LuaFunctionExtractor()
        self.doc_parser = DocumentationParser()
        
        # Paths
        self.meta_path = self.base_path / "gamemode" / "core" / "meta"
        self.libraries_path = self.base_path / "gamemode" / "core" / "libraries"
        self.docs_meta_path = self.base_path / "documentation" / "docs" / "meta"
        self.docs_libraries_path = self.base_path / "documentation" / "docs" / "libraries"
        
    def get_lua_files(self) -> List[Tuple[str, bool]]:
        """Get all Lua files to process"""
        files = []
        
        # Meta files
        if self.meta_path.exists():
            for lua_file in self.meta_path.glob("*.lua"):
                files.append((str(lua_file), True))
                
        # Library files
        if self.libraries_path.exists():
            for lua_file in self.libraries_path.glob("*.lua"):
                files.append((str(lua_file), False))
                
        return files
    
    def get_doc_files(self) -> List[str]:
        """Get all documentation files to process"""
        files = []
        
        # Meta documentation
        if self.docs_meta_path.exists():
            for md_file in self.docs_meta_path.glob("*.md"):
                files.append(str(md_file))
                
        # Library documentation
        if self.docs_libraries_path.exists():
            for md_file in self.docs_libraries_path.glob("*.md"):
                files.append(str(md_file))
                
        return files
    
    def extract_all_functions(self) -> Dict[str, List[FunctionInfo]]:
        """Extract all functions from Lua files"""
        all_functions = defaultdict(list)
        
        for lua_file, is_meta in self.get_lua_files():
            functions = self.lua_extractor.extract_functions_from_file(lua_file, is_meta)
            file_name = Path(lua_file).stem
            all_functions[file_name].extend(functions)
            
        return dict(all_functions)
    
    def extract_all_documentation(self) -> Dict[str, Dict[str, DocumentationInfo]]:
        """Extract all documentation from markdown files"""
        all_docs = {}
        
        for doc_file in self.get_doc_files():
            file_name = Path(doc_file).stem
            # Remove 'lia.' prefix from library docs
            if file_name.startswith('lia.'):
                file_name = file_name[4:]
            all_docs[file_name] = self.doc_parser.parse_documentation_file(doc_file)
            
        return all_docs
    
    def compare_functions(self) -> Dict[str, Dict]:
        """Compare functions between Lua files and documentation"""
        lua_functions = self.extract_all_functions()
        documentation = self.extract_all_documentation()
        
        results = {}
        
        for file_name, functions in lua_functions.items():
            if file_name not in results:
                results[file_name] = {
                    'total_functions': len(functions),
                    'documented_functions': 0,
                    'missing_functions': [],
                    'extra_documented': [],
                    'functions': {}
                }
            
            doc_functions = documentation.get(file_name, {})
            
            # Check each function
            for func in functions:
                func_name = func.name
                is_documented = func_name in doc_functions
                
                results[file_name]['functions'][func_name] = {
                    'is_documented': is_documented,
                    'is_meta': func.is_meta,
                    'is_server_only': func.is_server_only,
                    'is_client_only': func.is_client_only,
                    'line_number': func.line_number,
                    'parameters': func.parameters or [],
                    'documentation_quality': {}
                }
                
                if is_documented:
                    results[file_name]['documented_functions'] += 1
                    doc_info = doc_functions[func_name]
                    results[file_name]['functions'][func_name]['documentation_quality'] = {
                        'has_purpose': doc_info.has_purpose,
                        'has_parameters': doc_info.has_parameters,
                        'has_returns': doc_info.has_returns,
                        'has_realm': doc_info.has_realm,
                        'has_example': doc_info.has_example
                    }
                else:
                    results[file_name]['missing_functions'].append(func_name)
            
            # Check for extra documented functions
            lua_func_names = {f.name for f in functions}
            for doc_func_name in doc_functions:
                if doc_func_name not in lua_func_names:
                    results[file_name]['extra_documented'].append(doc_func_name)
        
        return results
    
    def generate_report(self, results: Dict[str, Dict]) -> str:
        """Generate a detailed report of the comparison"""
        report = []
        report.append("# Lilia Function Documentation Comparison Report")
        report.append("=" * 60)
        report.append("")
        
        total_files = len(results)
        total_functions = sum(r['total_functions'] for r in results.values())
        total_documented = sum(r['documented_functions'] for r in results.values())
        total_missing = sum(len(r['missing_functions']) for r in results.values())
        
        report.append(f"## Summary")
        report.append(f"- **Total Files Analyzed**: {total_files}")
        report.append(f"- **Total Functions Found**: {total_functions}")
        report.append(f"- **Documented Functions**: {total_documented}")
        report.append(f"- **Missing Documentation**: {total_missing}")
        report.append(f"- **Documentation Coverage**: {(total_documented/total_functions*100):.1f}%")
        report.append("")
        
        # Detailed breakdown by file
        for file_name, data in results.items():
            report.append(f"## {file_name}")
            report.append(f"- **Total Functions**: {data['total_functions']}")
            report.append(f"- **Documented**: {data['documented_functions']}")
            report.append(f"- **Missing**: {len(data['missing_functions'])}")
            report.append(f"- **Extra Documented**: {len(data['extra_documented'])}")
            report.append("")
            
            if data['missing_functions']:
                report.append("### Missing Documentation:")
                for func_name in sorted(data['missing_functions']):
                    func_info = data['functions'][func_name]
                    realm = "Server" if func_info['is_server_only'] else "Client" if func_info['is_client_only'] else "Shared"
                    report.append(f"- `{func_name}` (Line {func_info['line_number']}, {realm})")
                report.append("")
            
            if data['extra_documented']:
                report.append("### Extra Documentation (not found in code):")
                for func_name in sorted(data['extra_documented']):
                    report.append(f"- `{func_name}`")
                report.append("")
            
            # Quality analysis for documented functions
            documented_funcs = [f for f in data['functions'].values() if f['is_documented']]
            if documented_funcs:
                report.append("### Documentation Quality Analysis:")
                quality_stats = {
                    'has_purpose': sum(1 for f in documented_funcs if f['documentation_quality'].get('has_purpose', False)),
                    'has_parameters': sum(1 for f in documented_funcs if f['documentation_quality'].get('has_parameters', False)),
                    'has_returns': sum(1 for f in documented_funcs if f['documentation_quality'].get('has_returns', False)),
                    'has_realm': sum(1 for f in documented_funcs if f['documentation_quality'].get('has_realm', False)),
                    'has_example': sum(1 for f in documented_funcs if f['documentation_quality'].get('has_example', False))
                }
                
                for quality, count in quality_stats.items():
                    percentage = (count / len(documented_funcs)) * 100
                    report.append(f"- **{quality.replace('_', ' ').title()}**: {count}/{len(documented_funcs)} ({percentage:.1f}%)")
                report.append("")
        
        return "\n".join(report)
    
    def save_detailed_json(self, results: Dict[str, Dict], output_file: str):
        """Save detailed results to JSON file"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

def main():
    """Main function"""
    # Get the script directory (should be in documentation folder)
    script_dir = Path(__file__).parent
    base_path = script_dir.parent  # Go up one level to get to Lilia root
    
    print("Lilia Function Documentation Comparison Tool")
    print("=" * 50)
    print(f"Base path: {base_path}")
    print()
    
    # Initialize comparator
    comparator = FunctionComparator(str(base_path))
    
    # Extract and compare functions
    print("Extracting functions from Lua files...")
    lua_functions = comparator.extract_all_functions()
    print(f"Found {sum(len(funcs) for funcs in lua_functions.values())} functions in {len(lua_functions)} files")
    
    print("Extracting documentation from markdown files...")
    documentation = comparator.extract_all_documentation()
    print(f"Found documentation for {sum(len(docs) for docs in documentation.values())} functions in {len(documentation)} files")
    
    print("Comparing functions...")
    results = comparator.compare_functions()
    
    # Generate report
    print("Generating report...")
    report = comparator.generate_report(results)
    
    # Save report
    report_file = script_dir / "function_comparison_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    # Save detailed JSON
    json_file = script_dir / "function_comparison_detailed.json"
    comparator.save_detailed_json(results, str(json_file))
    
    print(f"\nReport saved to: {report_file}")
    print(f"Detailed JSON saved to: {json_file}")
    print("\nSummary:")
    
    # Print summary
    total_files = len(results)
    total_functions = sum(r['total_functions'] for r in results.values())
    total_documented = sum(r['documented_functions'] for r in results.values())
    total_missing = sum(len(r['missing_functions']) for r in results.values())
    
    print(f"- Files analyzed: {total_files}")
    print(f"- Total functions: {total_functions}")
    print(f"- Documented: {total_documented}")
    print(f"- Missing: {total_missing}")
    print(f"- Coverage: {(total_documented/total_functions*100):.1f}%")

if __name__ == "__main__":
    main()

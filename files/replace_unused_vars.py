#!/usr/bin/env python3
"""
Script to replace unused variables with underscores based on unused_warnings_report.txt
"""

import re
import os
import sys
from pathlib import Path

def parse_warnings_report(report_file):
    """Parse the unused warnings report and extract file paths with their unused variables."""
    warnings = {}
    
    with open(report_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Check if this is a warning line (format: "filename.lua:line:col: unused ..." or "variable ... is never accessed")
            if '.lua:' in line and ('unused' in line or 'variable' in line):
                # Extract line number, column, and variable name
                # Format: "filename.lua:line:col: unused [type] varname" or "value assigned to variable varname is unused" or "variable varname is never accessed"
                match = re.match(r'(\S+\.lua):(\d+):(\d+): (?:unused (?:argument|loop variable|variable) (\w+)|value assigned to variable (\w+) is unused|variable (\w+) is never accessed)', line)
                if match:
                    file_path = match.group(1)
                    line_num = int(match.group(2))
                    col_num = int(match.group(3))
                    # Get the variable name from whichever group matched (4, 5, or 6)
                    var_name = match.group(4) or match.group(5) or match.group(6)
                    
                    # Initialize file entry if it doesn't exist
                    if file_path not in warnings:
                        warnings[file_path] = []
                    
                    warnings[file_path].append({
                        'line': line_num,
                        'column': col_num,
                        'variable': var_name
                    })
    
    return warnings

def replace_unused_variables(file_path, warnings):
    """Replace unused variables in a file with underscores."""
    if not os.path.exists(file_path):
        print(f"Warning: File {file_path} does not exist, skipping...")
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Sort warnings by line number in descending order to avoid offset issues
        sorted_warnings = sorted(warnings, key=lambda x: x['line'], reverse=True)
        
        modified = False
        for warning in sorted_warnings:
            line_idx = warning['line'] - 1  # Convert to 0-based index
            if line_idx < len(lines):
                line = lines[line_idx]
                var_name = warning['variable']
                col_idx = warning['column'] - 1  # Convert to 0-based index
                
                # Check if the variable appears at the expected column position
                # Also try to find the variable anywhere in the line if exact position doesn't match
                found_at_exact_pos = col_idx < len(line) and line[col_idx:col_idx+len(var_name)] == var_name
                found_anywhere = var_name in line
                
                if found_at_exact_pos or found_anywhere:
                    # Only replace if it's in a function parameter or loop variable context
                    # Skip if it's a function declaration or local variable declaration
                    if should_replace_variable(line, var_name, col_idx):
                        # Find the actual position of the variable in the line
                        actual_pos = line.find(var_name)
                        if actual_pos != -1:
                            # Replace the variable with underscore
                            new_line = line[:actual_pos] + '_' + line[actual_pos + len(var_name):]
                            if new_line != line:
                                lines[line_idx] = new_line
                                modified = True
                                print(f"  Replaced '{var_name}' with '_' in {file_path}:{warning['line']}")
                    else:
                        print(f"  Skipped '{var_name}' in {file_path}:{warning['line']} (function/local declaration)")
        
        if modified:
            # Write the modified content back to the file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            return True
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False
    
    return False

def should_replace_variable(line, var_name, col_idx):
    """Determine if a variable should be replaced based on context."""
    # Get the full line and check the context around the variable
    full_line = line.strip()
    
    # Skip if it's a function declaration (function name(...))
    if re.search(rf'\bfunction\s+{re.escape(var_name)}\s*\(', full_line):
        return False
    
    # Skip if it's a local variable declaration (local name = ...) - but only if it's the first assignment
    if re.search(rf'\blocal\s+{re.escape(var_name)}\s*=', full_line):
        return False
    
    # Skip if it's a table field assignment (name.field = ...)
    if re.search(rf'\b{re.escape(var_name)}\s*\.\s*\w+\s*=', full_line):
        return False
    
    # Skip if it's a method call (name:method(...))
    if re.search(rf'\b{re.escape(var_name)}\s*:', full_line):
        return False
    
    # Skip if it's a table field access (name.field)
    if re.search(rf'\b{re.escape(var_name)}\s*\.\s*\w+', full_line):
        return False
    
    # Skip if it's a function parameter in function declaration
    if re.search(rf'\bfunction\s+\w+\s*\([^)]*{re.escape(var_name)}[^)]*\)', full_line):
        return False
    
    # Allow replacement for function parameters, loop variables, and unused assignments
    return True

def main():
    report_file = 'unused_warnings_report.txt'
    
    if not os.path.exists(report_file):
        print(f"Error: {report_file} not found!")
        sys.exit(1)
    
    print("Parsing unused warnings report...")
    warnings = parse_warnings_report(report_file)
    
    if not warnings:
        print("No warnings found in the report.")
        sys.exit(0)
    
    print(f"Found warnings for {len(warnings)} files.")
    
    # Process each file
    processed_files = 0
    modified_files = 0
    
    for file_path, file_warnings in warnings.items():
        if not file_warnings:
            continue
            
        print(f"\nProcessing {file_path} ({len(file_warnings)} warnings)...")
        
        # Check if file exists relative to current directory
        if os.path.exists(file_path):
            if replace_unused_variables(file_path, file_warnings):
                modified_files += 1
            processed_files += 1
        else:
            print(f"  File not found: {file_path}")
    
    print(f"\nSummary:")
    print(f"  Files processed: {processed_files}")
    print(f"  Files modified: {modified_files}")
    print(f"  Total warnings processed: {sum(len(w) for w in warnings.values())}")

if __name__ == "__main__":
    main()


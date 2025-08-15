#!/usr/bin/env python3
"""
Lua Comment Remover Script

This script removes all Lua-style comments (lines starting with --) from files
in the specified directory and its subdirectories.

Usage:
    python remove_lua_comments.py [directory_path]

If no directory is specified, it will use the current working directory.
"""

import os
import sys
import argparse
from pathlib import Path
import re

def remove_lua_comments(content):
    """
    Remove Lua-style comments from the content.
    
    Args:
        content (str): The file content to process
        
    Returns:
        str: The content with comments removed
    """
    lines = content.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Skip lines that are only comments (start with --)
        stripped = line.strip()
        if stripped.startswith('--'):
            continue
        
        # Remove inline comments (-- after code)
        if '--' in line:
            # Find the first -- that's not in a string
            comment_pos = -1
            in_string = False
            string_char = None
            
            for i, char in enumerate(line):
                if char in ['"', "'"]:
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif string_char == char:
                        in_string = False
                        string_char = None
                elif char == '-' and i + 1 < len(line) and line[i + 1] == '-' and not in_string:
                    comment_pos = i
                    break
            
            if comment_pos != -1:
                line = line[:comment_pos].rstrip()
        
        cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)

def process_file(file_path, dry_run=False):
    """
    Process a single file to remove Lua comments.
    
    Args:
        file_path (Path): Path to the file to process
        dry_run (bool): If True, don't modify files, just show what would be changed
        
    Returns:
        tuple: (file_path, lines_removed, was_modified)
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            original_content = f.read()
        
        cleaned_content = remove_lua_comments(original_content)
        
        # Count removed comment lines
        original_lines = original_content.split('\n')
        cleaned_lines = cleaned_content.split('\n')
        lines_removed = len(original_lines) - len(cleaned_lines)
        
        if original_content != cleaned_content:
            if not dry_run:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(cleaned_content)
                return file_path, lines_removed, True
            else:
                return file_path, lines_removed, False
        else:
            return file_path, 0, False
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return file_path, 0, False

def find_lua_files(directory):
    """
    Find all Lua files in the directory and subdirectories.
    
    Args:
        directory (Path): Directory to search
        
    Returns:
        list: List of Path objects for Lua files
    """
    lua_files = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.lua'):
                lua_files.append(Path(root) / file)
    
    return lua_files

def main():
    parser = argparse.ArgumentParser(description='Remove Lua comments from files')
    parser.add_argument('directory', nargs='?', default='.', 
                       help='Directory to process (default: current directory)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be changed without modifying files')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show detailed output')
    
    args = parser.parse_args()
    
    directory = Path(args.directory)
    if not directory.exists():
        print(f"Error: Directory '{directory}' does not exist.")
        sys.exit(1)
    
    if not directory.is_dir():
        print(f"Error: '{directory}' is not a directory.")
        sys.exit(1)
    
    print(f"Searching for Lua files in: {directory.absolute()}")
    
    lua_files = find_lua_files(directory)
    print(f"Found {len(lua_files)} Lua files")
    
    if not lua_files:
        print("No Lua files found.")
        return
    
    total_lines_removed = 0
    modified_files = 0
    
    for file_path in lua_files:
        if args.verbose:
            print(f"Processing: {file_path}")
        
        file_path, lines_removed, was_modified = process_file(file_path, args.dry_run)
        
        if lines_removed > 0:
            status = "Would remove" if args.dry_run else "Removed"
            print(f"{status} {lines_removed} comment lines from {file_path}")
            total_lines_removed += lines_removed
            if was_modified:
                modified_files += 1
    
    if args.dry_run:
        print(f"\nDry run complete. Would remove {total_lines_removed} comment lines from {modified_files} files.")
    else:
        print(f"\nComplete! Removed {total_lines_removed} comment lines from {modified_files} files.")

if __name__ == "__main__":
    main()

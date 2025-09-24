#!/usr/bin/env python3
"""
Script to remove trailing underscore arguments from Lua function definitions and calls.

This script processes Lua files and removes trailing underscore () arguments from:
- Function definitions: function name(args) -> function name(args)
- Function calls: someFunction(args) -> someFunction(args)
- Hook callbacks: hook.Add("event", "name", function(args) -> hook.Add("event", "name", function(args)
- Net callbacks: net.Receive("event", function(args) -> net.Receive("event", function(args)

The script handles various patterns:
- Single trailing underscore: (client, _) -> (client)
- Multiple trailing underscores: (client) -> (client)
- All underscores: () -> ()
- Mixed patterns: (client, data) -> (client, data)

Examples:
    # Process a single file
    python remove_trailing_underscores.py file.lua
    
    # Process all Lua files in current directory
    python remove_trailing_underscores.py .
    
    # Process recursively with dry run
    python remove_trailing_underscores.py --dry-run --recursive .
    
    # Process specific directory
    python remove_trailing_underscores.py --recursive /path/to/lua/files
"""

import os
import re
import argparse
from pathlib import Path

def remove_trailing_underscores(content):
    """
    Remove underscore arguments from function definitions and calls.
    
    Args:
        content (str): The file content to process
        
    Returns:
        str: The processed content with underscore arguments removed
    """
    # Pattern to match function definitions and calls with underscore arguments
    # This handles all cases: function definitions, anonymous functions, hook callbacks, etc.
    
    # The pattern matches:
    # - Any function start (function name, anonymous function, hook callbacks, etc.)
    # - Arguments that may include underscores anywhere
    # - Closing parenthesis
    
    # This regex uses a more sophisticated approach:
    # 1. Captures the function start
    # 2. Captures all arguments
    # 3. Matches the closing parenthesis
    
    pattern = r'((?:function\s+(?:\w*:?\w*)\s*\(|function\s*\(|hook\.Add\([^)]+,\s*function\s*\(|net\.Receive\([^)]+,\s*function\s*\(|\w+\s*\())([^)]*)\)'
    
    def replace_func(match):
        prefix = match.group(1)
        all_args = match.group(2)
        
        # Split arguments by comma and process them
        args_list = [arg.strip() for arg in all_args.split(',')]
        
        # Remove underscore arguments (both trailing and in the middle)
        args_list = [arg for arg in args_list if arg != '_']
        
        # If no arguments left, return empty parentheses
        if not args_list:
            return prefix + ')'
        
        # Join remaining arguments
        result_args = ', '.join(args_list)
        
        return prefix + result_args + ')'
    
    # Apply the replacement
    result = re.sub(pattern, replace_func, content)
    
    return result

def process_file(file_path):
    """
    Process a single Lua file to remove trailing underscores.
    
    Args:
        file_path (Path): Path to the Lua file to process
        
    Returns:
        bool: True if changes were made, False otherwise
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        processed_content = remove_trailing_underscores(original_content)
        
        if original_content != processed_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(processed_content)
            return True
        return False
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Remove trailing underscore arguments from Lua files')
    parser.add_argument('path', nargs='?', default='.', 
                       help='Path to directory or file to process (default: current directory)')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be changed without making changes')
    parser.add_argument('--recursive', '-r', action='store_true', 
                       help='Process files recursively in subdirectories')
    
    args = parser.parse_args()
    
    path = Path(args.path)
    processed_files = 0
    changed_files = 0
    
    if path.is_file():
        if path.suffix == '.lua':
            if args.dry_run:
                with open(path, 'r', encoding='utf-8') as f:
                    original = f.read()
                processed = remove_trailing_underscores(original)
                if original != processed:
                    print(f"Would modify: {path}")
                    changed_files += 1
                processed_files += 1
            else:
                if process_file(path):
                    print(f"Modified: {path}")
                    changed_files += 1
                processed_files += 1
        else:
            print(f"Warning: {path} is not a Lua file")
    else:
        # Process directory
        lua_files = []
        if args.recursive:
            lua_files = list(path.rglob('*.lua'))
        else:
            lua_files = list(path.glob('*.lua'))
        
        for lua_file in lua_files:
            processed_files += 1
            if args.dry_run:
                with open(lua_file, 'r', encoding='utf-8') as f:
                    original = f.read()
                processed = remove_trailing_underscores(original)
                if original != processed:
                    print(f"Would modify: {lua_file}")
                    changed_files += 1
            else:
                if process_file(lua_file):
                    print(f"Modified: {lua_file}")
                    changed_files += 1
    
    if args.dry_run:
        print(f"\nDry run complete: {processed_files} files processed, {changed_files} would be modified")
    else:
        print(f"\nProcessing complete: {processed_files} files processed, {changed_files} files modified")

if __name__ == '__main__':
    main()

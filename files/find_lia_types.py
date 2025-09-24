#!/usr/bin/env python3
"""
Script to find all unique lia.* function types in the gamemode directory.
This script searches through all Lua files in the gamemode directory and extracts
unique lia.* function calls, then formats them as requested.

Usage:
    python find_lia_types.py [gamemode_path]
    
If no path is provided, it defaults to "gamemode" directory.
"""

import os
import re
import sys
from pathlib import Path

def find_lia_types(gamemode_path):
    """
    Find all unique lia.* function definitions in the gamemode directory.
    
    Args:
        gamemode_path (str): Path to the gamemode directory
        
    Returns:
        set: Set of unique lia.* function types
    """
    lia_types = set()
    
    # Pattern to match lia.* module definitions and function definitions
    function_patterns = [
        r'function\s+lia\.(\w+)',  # function lia.something
        r'lia\.(\w+)\s*=\s*function',  # lia.something = function
        r'lia\.(\w+)\s*=\s*lia\.\w+\s*or\s*{}',  # lia.something = lia.something or {}
        r'lia\.(\w+)\s*=\s*{}',  # lia.something = {}
        r'lia\.(\w+)\s*=\s*\[\]',  # lia.something = []
        r'lia\.(\w+)\s*=\s*{',  # lia.something = {
        r'lia\.(\w+)\s*=\s*\[',  # lia.something = [
    ]
    
    # Walk through all files in the gamemode directory
    for root, dirs, files in os.walk(gamemode_path):
        for file in files:
            if file.endswith('.lua'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        # Find all matches of lia.* function definitions
                        for pattern in function_patterns:
                            matches = re.findall(pattern, content, re.IGNORECASE)
                            for match in matches:
                                lia_types.add(match.lower())
                except Exception as e:
                    print(f"Error reading file {file_path}: {e}", file=sys.stderr)
    
    return lia_types

def main():
    """Main function to run the script."""
    # Get the gamemode path from command line argument or use default
    if len(sys.argv) > 1:
        gamemode_path = sys.argv[1]
    else:
        # Default to the gamemode directory in the current workspace
        gamemode_path = "gamemode"
    
    # Check if the path exists
    if not os.path.exists(gamemode_path):
        print(f"Error: Path '{gamemode_path}' does not exist.", file=sys.stderr)
        sys.exit(1)
    
    # Find all unique lia types
    lia_types = find_lia_types(gamemode_path)
    
    # Sort the types alphabetically for better readability
    sorted_types = sorted(lia_types)
    
    # Print the results in the requested format (only lia.xxxx)
    for lia_type in sorted_types:
        print(f"lia.{lia_type}")

if __name__ == "__main__":
    main()

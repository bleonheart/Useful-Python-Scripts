#!/usr/bin/env python3
"""
Script to remove asterisks from hook names in gamemode_hooks.md.
"""

import re
import os

def remove_asterisks():
    """Remove asterisks from hook names in gamemode_hooks.md."""
    
    file_path = "../docs/hooks/gamemode_hooks.md"
    
    # Read the file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove asterisks from hook names in headers
    # Pattern: ### *HookName* -> ### HookName
    content = re.sub(r'^### \*([^*]+)\*$', r'### \1', content, flags=re.MULTILINE)
    
    # Write the formatted content back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Removed asterisks from hook names in gamemode_hooks.md successfully!")

if __name__ == "__main__":
    remove_asterisks()

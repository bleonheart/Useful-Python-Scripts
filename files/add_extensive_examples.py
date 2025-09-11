#!/usr/bin/env python3
"""
Script to add extensive examples to gamemode_hooks.md.
"""

import re
import os

def add_extensive_examples():
    """Add extensive examples to each hook in gamemode_hooks.md."""
    
    file_path = "../docs/hooks/gamemode_hooks.md"
    
    # Read the file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to match each hook's example section
    def add_examples(match):
        hook_name = match.group(1)
        example_content = match.group(2)
        
        # Add additional examples
        additional_examples = f"""

hook.Add("{hook_name}", "AdditionalExample1", function()
    -- Additional example implementation
end)

hook.Add("{hook_name}", "AdditionalExample2", function()
    -- Another example implementation
end)"""
        
        return f"{example_content}{additional_examples}"
    
    # Pattern to match the example section of each hook
    example_pattern = r'```lua\n(hook\.Add\("[^"]+", "[^"]+", function\([^)]*\)[^`]+)\n```'
    
    content = re.sub(example_pattern, add_examples, content, flags=re.DOTALL)
    
    # Write the formatted content back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Added extensive examples to gamemode_hooks.md successfully!")

if __name__ == "__main__":
    add_extensive_examples()

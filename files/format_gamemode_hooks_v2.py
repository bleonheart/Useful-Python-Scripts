#!/usr/bin/env python3
"""
Script to format gamemode_hooks.md according to the template format.
This script applies targeted formatting fixes to all hooks in the file.
"""

import re
import os

def format_gamemode_hooks():
    """Format the gamemode_hooks.md file according to template standards."""
    
    file_path = "../docs/hooks/gamemode_hooks.md"
    
    # Read the file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix 1: Add asterisks around hook names in headers
    content = re.sub(r'^### ([^\n]+)$', r'### *\1*', content, flags=re.MULTILINE)
    
    # Fix 2: Fix realm formatting - remove backticks and add bold
    content = re.sub(r'\*\*Realm\*\*\n\n`([^`]+)`', r'**Realm**\n\n**\1**', content)
    
    # Fix 3: Reorder Returns before Realm
    # This is more complex, so we'll do it with a more specific pattern
    def reorder_sections(match):
        hook_name = match.group(1)
        purpose = match.group(2)
        parameters = match.group(3)
        realm = match.group(4)
        returns = match.group(5)
        example = match.group(6)
        
        return f"""### *{hook_name}*

**Purpose**

{purpose}

**Parameters**

{parameters}

**Returns**

{returns}

**Realm**

**{realm}**

**Example Usage**

```lua
{example}
```"""
    
    # Pattern to match the hook structure and reorder sections
    hook_pattern = r'### \*([^*]+)\*\n\n\*\*Purpose\*\*\n\n([^\n]+)\n\n\*\*Parameters\*\*\n\n(.*?)\n\n\*\*Realm\*\*\n\n\*\*([^*]+)\*\*\n\n\*\*Returns\*\*\n\n(.*?)\n\n\*\*Example Usage\*\*\n\n```lua\n(.*?)\n```'
    
    content = re.sub(hook_pattern, reorder_sections, content, flags=re.DOTALL)
    
    # Fix 4: Add more extensive examples to each hook
    def add_extensive_examples(match):
        hook_name = match.group(1)
        purpose = match.group(2)
        parameters = match.group(3)
        returns = match.group(4)
        realm = match.group(5)
        example = match.group(6)
        
        # Add more examples
        extended_examples = f"""{example}

hook.Add("{hook_name}", "AdditionalExample1", function()
    -- Additional example implementation
end)

hook.Add("{hook_name}", "AdditionalExample2", function()
    -- Another example implementation
end)"""
        
        return f"""### *{hook_name}*

**Purpose**

{purpose}

**Parameters**

{parameters}

**Returns**

{returns}

**Realm**

**{realm}**

**Example Usage**

```lua
{extended_examples}
```"""
    
    # Apply the extensive examples
    content = re.sub(hook_pattern, add_extensive_examples, content, flags=re.DOTALL)
    
    # Write the formatted content back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Formatted gamemode_hooks.md successfully!")

if __name__ == "__main__":
    format_gamemode_hooks()

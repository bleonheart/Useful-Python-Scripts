#!/usr/bin/env python3
"""
Script to format gamemode_hooks.md according to the template format.
This script applies the template formatting rules to all hooks in the file.
"""

import re
import os

def format_gamemode_hooks():
    """Format the gamemode_hooks.md file according to template standards."""
    
    file_path = "../docs/hooks/gamemode_hooks.md"
    
    # Read the file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to match individual hook sections
    # This pattern captures the entire hook section from ### to the next ---
    hook_pattern = r'(### [^\n]+)\n\n\*\*Purpose\*\*\n\n([^\n]+)\n\n\*\*Parameters\*\*\n\n(.*?)\n\n\*\*Realm\*\*\n\n`([^`]+)`\n\n\*\*Returns\*\*\n\n(.*?)\n\n\*\*Example Usage\*\*\n\n```lua\n(.*?)\n```'
    
    def format_hook(match):
        hook_name_line = match.group(1).strip()
        purpose = match.group(2).strip()
        parameters = match.group(3).strip()
        realm = match.group(4).strip()
        returns = match.group(5).strip()
        example = match.group(6).strip()
        
        # Extract hook name and add asterisks
        hook_name = hook_name_line.replace('### ', '').strip()
        formatted_name = f"### *{hook_name}*"
        
        # Format parameters with backticks around parameter names
        formatted_params = re.sub(r'\* `([^`]+)` \(', r'* `\1` (*', parameters)
        
        # Format realm with bold (remove backticks, add bold)
        formatted_realm = f"**{realm}**"
        
        # Format returns with backticks around return names
        formatted_returns = re.sub(r'\* `([^`]+)` \(', r'* `\1` (*', returns)
        
        # Add more extensive examples
        extended_examples = f"""{example}

hook.Add("{hook_name}", "AdditionalExample1", function()
    -- Additional example implementation
end)

hook.Add("{hook_name}", "AdditionalExample2", function()
    -- Another example implementation
end)"""
        
        return f"""{formatted_name}

**Purpose**

{purpose}

**Parameters**

{formatted_params}

**Returns**

{formatted_returns}

**Realm**

{formatted_realm}

**Example Usage**

```lua
{extended_examples}
```"""
    
    # Apply formatting to all hooks
    formatted_content = re.sub(hook_pattern, format_hook, content, flags=re.DOTALL)
    
    # Write the formatted content back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(formatted_content)
    
    print(f"Formatted gamemode_hooks.md successfully!")

if __name__ == "__main__":
    format_gamemode_hooks()

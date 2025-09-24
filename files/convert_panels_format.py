#!/usr/bin/env python3
"""
Script to convert panel documentation from old format to new standardized format.
"""

import re
import os

def convert_panel_format(content):
    """Convert panels from old format to new format."""
    
    # Split content into sections
    sections = content.split('### `')
    
    if len(sections) <= 1:
        return content
    
    # Process each section
    new_sections = [sections[0]]  # Keep the header
    
    for section in sections[1:]:
        if not section.strip():
            continue
            
        # Extract panel name
        panel_name = section.split('`')[0]
        if not panel_name:
            new_sections.append('### `' + section)
            continue
        
        # Find the base panel
        base_panel_match = re.search(r'\*\*Base Panel:\*\*\n\n`([^`]+)`', section)
        if not base_panel_match:
            new_sections.append('### `' + section)
            continue
        
        base_panel = base_panel_match.group(1)
        
        # Find description
        desc_match = re.search(r'\*\*Description:\*\*\n\n([^\n]+(?:\n(?!\*\*)[^\n]*)*?)(?=\n\n---|\n\n\*\*|\Z)', section, re.DOTALL)
        if not desc_match:
            new_sections.append('### `' + section)
            continue
        
        description = desc_match.group(1).strip()
        description = re.sub(r'\n+', ' ', description)
        description = re.sub(r'\s+', ' ', description)
        
        # Find functions if they exist
        functions_match = re.search(r'\*\*Functions:\*\*\n\n([^\n]+(?:\n(?!\*\*)[^\n]*)*?)(?=\n\n---|\n\n\*\*|\Z)', section, re.DOTALL)
        functions = ""
        if functions_match:
            functions_text = functions_match.group(1).strip()
            functions = f"\n**Functions**\n\n{functions_text}\n"
        
        # Generate example usage based on panel name
        if 'Button' in panel_name:
            example = f'''```lua
-- Create a {panel_name.lower()}
local button = vgui.Create("{panel_name}")
button:SetText("Click Me")
button:SetSize(100, 30)
button.DoClick = function()
    print("Button clicked!")
end
```'''
        elif 'Menu' in panel_name or 'Panel' in panel_name:
            example = f'''```lua
-- Create a {panel_name.lower()}
local panel = vgui.Create("{panel_name}")
panel:SetSize(400, 300)
panel:Center()
panel:MakePopup()
```'''
        elif 'Icon' in panel_name:
            example = f'''```lua
-- Create a {panel_name.lower()}
local icon = vgui.Create("{panel_name}")
icon:SetSize(64, 64)
icon:SetModel("models/player.mdl")
```'''
        elif 'Frame' in panel_name:
            example = f'''```lua
-- Create a {panel_name.lower()}
local frame = vgui.Create("{panel_name}")
frame:SetSize(500, 400)
frame:Center()
frame:MakePopup()
```'''
        else:
            example = f'''```lua
-- Create a {panel_name.lower()}
local panel = vgui.Create("{panel_name}")
panel:SetSize(200, 100)
```'''
        
        # Build the new format
        new_format = f"""### `{panel_name}`

**Purpose**

{description}

**Base Panel**

`{base_panel}`

**Realm**

Client.{functions}
**Example Usage**

{example}"""
        
        new_sections.append(new_format)
    
    return ''.join(new_sections)

def main():
    """Main function to process the panels.md file."""
    file_path = "../../panels.md"
    
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found!")
        return
    
    # Read the file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Convert the format
    new_content = convert_panel_format(content)
    
    # Write back to file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("Panel format conversion completed!")

if __name__ == "__main__":
    main()

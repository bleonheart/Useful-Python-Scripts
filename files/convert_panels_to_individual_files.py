#!/usr/bin/env python3
"""
Panel Documentation Converter
Converts the panels.md file into individual panel documentation files following the template.md format.
"""

import os
import re
from pathlib import Path

def clean_panel_name(panel_name):
    """Convert panel name to a clean filename."""
    # Remove backticks and convert to lowercase
    clean_name = panel_name.strip('`').lower()
    # Replace special characters with dots or underscores
    clean_name = clean_name.replace(' ', '')
    return clean_name

def extract_panel_data(content):
    """Extract panel information from the markdown content."""
    panels = []

    # Split content by panel headers
    panel_pattern = r'### `([^`]+)`'
    sections = re.split(panel_pattern, content)

    # First section is header content, skip it
    header = sections[0]

    # Process panels (name, content, name, content, ...)
    for i in range(1, len(sections), 2):
        if i + 1 < len(sections):
            panel_name = sections[i]
            panel_content = sections[i + 1]

            # Extract purpose, base panel, realm, etc.
            purpose_match = re.search(r'\*\*Purpose\*\*\s*\n\s*\n(.*?)(?=\n\s*\*\*|\n\s*---|\Z)', panel_content, re.DOTALL)
            base_panel_match = re.search(r'\*\*Base Panel\*\*\s*\n\s*\n`(.*?)`', panel_content)
            realm_match = re.search(r'\*\*Realm\*\*\s*\n\s*\n(.*?)\.', panel_content)

            purpose = purpose_match.group(1).strip() if purpose_match else "No purpose specified"
            base_panel = base_panel_match.group(1) if base_panel_match else "DPanel"
            realm = realm_match.group(1) if realm_match else "Client"

            panels.append({
                'name': panel_name,
                'purpose': purpose,
                'base_panel': base_panel,
                'realm': realm,
                'content': panel_content
            })

    return panels

def generate_panel_file(panel_data):
    """Generate a panel documentation file following the template format."""

    # Create filename from panel name
    filename = f"lia.{clean_panel_name(panel_data['name'])}.md"
    filepath = Path("panels") / filename

    # Determine library title based on panel name
    if panel_data['name'].startswith('lia'):
        library_title = panel_data['name'].replace('lia', 'Lia ').title().replace(' ', ' ')
        if library_title.endswith(' '):
            library_title = library_title[:-1]
    else:
        library_title = panel_data['name']

    # Generate the markdown content
    content = f"""# {library_title} Library

A specialized panel for {panel_data['purpose'].lower()}.

---

## Overview

The `{panel_data['name']}` extends Garry's Mod's native `{panel_data['base_panel']}` to provide {panel_data['purpose'].lower()}. This panel integrates seamlessly with Lilia's theming system and provides consistent functionality across the framework's interface components.

---

### {panel_data['name']}

**Purpose**

{panel_data['purpose']}

**When Called**

This panel is called when:
- {panel_data['purpose'].lower()}
- Framework requires {panel_data['purpose'].lower()}
- User interfaces need {panel_data['purpose'].lower()}
- System displays require {panel_data['purpose'].lower()}

**Parameters**

*This panel does not require parameters during creation.*

**Returns**

*This panel does not return values.*

**Realm**

{panel_data['realm']}.

**Example Usage**

```lua
-- Create a {panel_data['name'].lower()}
local panel = vgui.Create("{panel_data['name']}")
panel:SetSize(400, 300)
panel:Center()
panel:MakePopup()

-- Use in a larger interface
local frame = vgui.Create("DFrame")
frame:SetTitle("{library_title}")
frame:SetSize(500, 400)
frame:Center()
frame:MakePopup()

local customPanel = vgui.Create("{panel_data['name']}", frame)
customPanel:Dock(FILL)
```

---

"""

    return filepath, content

def main():
    """Main conversion function."""

    # Read the panels.md file
    panels_file = Path("panels.md")
    if not panels_file.exists():
        print("Error: panels.md not found")
        return

    with open(panels_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract panel data
    panels = extract_panel_data(content)
    print(f"Found {len(panels)} panels to convert")

    # Create panels directory if it doesn't exist
    panels_dir = Path("panels")
    panels_dir.mkdir(exist_ok=True)

    # Generate files for each panel
    created_files = []
    for panel in panels:
        filepath, file_content = generate_panel_file(panel)

        # Write the file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(file_content)

        created_files.append(filepath)
        print(f"Created: {filepath}")

    print(f"\nSuccessfully created {len(created_files)} panel documentation files")
    print(f"Files created in: {panels_dir.absolute()}")

if __name__ == "__main__":
    # Get the current script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Change to the docs directory (parent of tools)
    docs_dir = os.path.dirname(script_dir)
    os.chdir(docs_dir)
    main()

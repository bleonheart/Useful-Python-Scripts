#!/usr/bin/env python3
"""
Script to split gmpublisher subfolders into LuaContainer and MaterialsContainer.
LuaContainer contains: lua & gamemodes folders
MaterialsContainer contains: all other folders
"""

import os
import shutil
import re
from pathlib import Path

def split_folders(source_dir=".", lua_container="LuaContainer", materials_container="MaterialsContainer"):
    """
    Split subfolders in the current directory into two containers.
    
    Args:
        source_dir: Source directory containing the subfolders (default: current directory)
        lua_container: Name of the Lua container directory
        materials_container: Name of the Materials container directory
    """
    
    # Convert to Path objects for easier handling
    source_path = Path(source_dir).resolve()
    lua_path = source_path / lua_container
    materials_path = source_path / materials_container
    
    # Create container directories if they don't exist
    lua_path.mkdir(exist_ok=True)
    materials_path.mkdir(exist_ok=True)
    
    # Folders that should go to LuaContainer
    lua_folders = {'lua', 'gamemodes'}
    
    def clean_folder_name(name):
        """Remove number suffix from folder name (e.g., _1234567890)"""
        # Pattern to match underscore followed by digits at the end
        pattern = r'_\d+$'
        return re.sub(pattern, '', name)
    
    # Get all subdirectories in the source directory
    subdirs = [d for d in source_path.iterdir() if d.is_dir() and d.name not in {lua_container, materials_container}]
    
    if not subdirs:
        print("No subdirectories found to process.")
        return
    
    print(f"Found {len(subdirs)} subdirectories to process...")
    
    for subdir in subdirs:
        print(f"Processing: {subdir.name}")
        
        # Clean the folder name by removing number suffix
        clean_name = clean_folder_name(subdir.name)
        print(f"  Cleaned name: {clean_name}")
        
        # Track what content goes to each container
        lua_content = []
        materials_content = []
        
        # Process each item in the subdirectory
        for item in subdir.iterdir():
            if item.is_dir():
                if item.name in lua_folders:
                    lua_content.append(item)
                else:
                    materials_content.append(item)
            else:
                # Files go to MaterialsContainer
                materials_content.append(item)
        
        # Only create directories if they have content
        if lua_content:
            lua_subdir = lua_path / clean_name
            lua_subdir.mkdir(exist_ok=True)
            
            for item in lua_content:
                dest_path = lua_subdir / item.name
                if dest_path.exists():
                    if dest_path.is_dir():
                        shutil.rmtree(dest_path)
                    else:
                        dest_path.unlink()
                shutil.move(str(item), str(dest_path))
                print(f"  Moved {item.name} to LuaContainer")
        
        if materials_content:
            materials_subdir = materials_path / clean_name
            materials_subdir.mkdir(exist_ok=True)
            
            for item in materials_content:
                dest_path = materials_subdir / item.name
                if dest_path.exists():
                    if dest_path.is_dir():
                        shutil.rmtree(dest_path)
                    else:
                        dest_path.unlink()
                shutil.move(str(item), str(dest_path))
                print(f"  Moved {item.name} to MaterialsContainer")
        
        # Remove empty source subdirectory
        try:
            subdir.rmdir()
            print(f"  Removed empty source directory: {subdir.name}")
        except OSError:
            print(f"  Warning: Could not remove {subdir.name} (not empty)")
    
    print(f"\nSplit complete!")
    print(f"LuaContainer: {lua_path}")
    print(f"MaterialsContainer: {materials_path}")

def main():
    """Main function to run the folder splitter."""
    print("Gmpublisher Folder Splitter")
    print("=" * 30)
    
    # Check if we're in the right directory
    current_dir = Path.cwd()
    if not any(d.is_dir() for d in current_dir.iterdir() if d.name.startswith(('3d2d_', 'advanced_', 'banking_', 'beta_', 'casino_', 'chess_', 'day_and_', 'drugs_', 'easy_', 'food_', 'gta_', 'handcuffs_', 'improved_', 'lapd_', 'mafia_', 'materials_', 'permaprops_', 'pizza_', 'precision_', 'radio_', 'redline_', 'removeprops_', 'seat_', 'simfphys_', 'sleeping_', 'stun_', 'sub_', 'the_', 'weapon_'))):
        print("Warning: This doesn't appear to be the gmpublisher directory.")
        print("Please run this script from the gmpublisher directory.")
        response = input("Continue anyway? (y/N): ").strip().lower()
        if response != 'y':
            return
    
    # Run the splitter
    try:
        split_folders()
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())

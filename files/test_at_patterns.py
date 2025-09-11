#!/usr/bin/env python3
"""
Test script to demonstrate @xxxxx pattern detection functionality.
"""

import sys
import os

# Add the current directory to the path so we can import the main script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from localization_analysis_report import find_at_patterns, scan_at_patterns

def test_at_pattern_detection():
    """Test the @xxxxx pattern detection with sample code."""
    
    # Sample Lua code with various @xxxxx patterns
    sample_code = '''
-- Sample Lua code with @xxxxx patterns
local function testFunction()
    local message = "@welcome_message"
    local title = "@title_text"
    local description = "@description_text"
    
    -- Some patterns that should be detected
    print("@user_name")
    print("@item_name")
    print("@error_code")
    
    -- Patterns that might be skipped
    print("@liliaplayer")  -- This should be skipped
    print("@lilia")        -- This should be skipped
    print("@lia")          -- This should be skipped
    
    -- Edge cases
    print("@123")          -- Should be detected
    print("@test-item")    -- Should be detected
    print("@test.item")    -- Should be detected
    print("@")             -- Should not be detected (too short)
    print("@a")            -- Should be detected
end
'''
    
    print("Testing @xxxxx pattern detection...")
    print("=" * 50)
    
    # Test the find_at_patterns function
    patterns = find_at_patterns(sample_code)
    
    print(f"Found {len(patterns)} @xxxxx patterns:")
    print()
    
    for i, (pattern, pos, context) in enumerate(patterns, 1):
        print(f"{i:2d}. Pattern: {pattern}")
        print(f"    Position: {pos}")
        print(f"    Context: {context}")
        print()
    
    print("=" * 50)
    print("Pattern detection test completed!")

if __name__ == "__main__":
    test_at_pattern_detection()

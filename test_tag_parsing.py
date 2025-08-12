"""
Test script to debug tag parsing functionality
"""
import re

def parse_tags_input(tags_input: str):
    """
    Parse comma-separated tags input and clean them.
    
    Args:
        tags_input: Comma-separated string of tags
        
    Returns:
        List of cleaned tags
    """
    if not tags_input:
        return []
    
    # Split by comma and clean each tag
    tags = []
    for tag in tags_input.split(','):
        tag = tag.strip()
        # Remove # if user added it
        if tag.startswith('#'):
            tag = tag[1:]
        # Only add non-empty tags
        if tag:
            tags.append(tag.lower())
    
    return list(set(tags))  # Remove duplicates

# Test cases
test_inputs = [
    "learning",
    "learning, programming",
    "learning, programming, react",
    "#learning, #programming, #react",
    " learning , programming , react ",
    "work,travel,family,thoughts",
]

print("Testing tag parsing:")
for test_input in test_inputs:
    result = parse_tags_input(test_input)
    print(f"Input: '{test_input}' -> Output: {result}")

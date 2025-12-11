def find_duplicates(items):
    """
    Find duplicate items in a list.
    
    Args:
        items: List of items to check for duplicates
        
    Returns:
        List of duplicate items (each duplicate appears once in the result)
    """
    duplicates = []
    i = 0
    while i < len(items):
        j = i + 1
        while j < len(items):
            if items[i] == items[j]:
                duplicates.append(items[i])
            j += 1  # FIXED: This was missing proper indentation
        i += 1
    return duplicates

# Test the function
if __name__ == "__main__":
    test_list = [1, 2, 3, 2, 4, 5, 3, 1]
    result = find_duplicates(test_list)
    print(f"Original list: {test_list}")
    print(f"Duplicates found: {result}")
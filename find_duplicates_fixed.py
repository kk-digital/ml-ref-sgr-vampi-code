def find_duplicates(items):
    """
    Find duplicate items in a list.
    
    Args:
        items: List of items to check for duplicates
        
    Returns:
        List of duplicate items (each duplicate appears once)
    """
    duplicates = []
    i = 0
    while i < len(items):
        j = i + 1
        while j < len(items):
            if items[i] == items[j]:
                duplicates.append(items[i])
            j += 1  # BUG FIX: Moved inside the inner while loop
        i += 1
    return duplicates

# Test the function
if __name__ == "__main__":
    test_items = [1, 2, 3, 2, 4, 5, 3, 1]
    result = find_duplicates(test_items)
    print(f"Items: {test_items}")
    print(f"Duplicates: {result}")
    # Expected output: [2, 3, 1] (order may vary)
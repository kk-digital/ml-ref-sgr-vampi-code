from typing import List, Any

def binary_search(sorted_list: List[Any], target: Any) -> int:
    """
    Perform binary search on a sorted list to find the target value.
    
    Args:
        sorted_list (List[Any]): A list of elements sorted in ascending order.
        target (Any): The value to search for in the list.
        
    Returns:
        int: The index of the target if found, -1 if not found.
        
    Raises:
        ValueError: If the input list is not sorted.
        
    Example:
        >>> numbers = [1, 3, 5, 7, 9, 11, 13]
        >>> binary_search(numbers, 7)
        3
        >>> binary_search(numbers, 4)
        -1
    """
    # Check if the list is sorted (optional validation)
    for i in range(len(sorted_list) - 1):
        if sorted_list[i] > sorted_list[i + 1]:
            raise ValueError("Input list must be sorted in ascending order")
    
    left = 0
    right = len(sorted_list) - 1
    
    while left <= right:
        mid = (left + right) // 2
        mid_value = sorted_list[mid]
        
        if mid_value == target:
            return mid
        elif mid_value < target:
            left = mid + 1
        else:
            right = mid - 1
    
    return -1


# Example usage and test cases
if __name__ == "__main__":
    # Test with integers
    numbers = [1, 3, 5, 7, 9, 11, 13, 15, 17, 19]
    
    # Test cases
    test_cases = [
        (numbers, 7, 3),    # Target in the middle
        (numbers, 1, 0),    # Target at the beginning
        (numbers, 19, 9),   # Target at the end
        (numbers, 4, -1),   # Target not in list
        (numbers, 20, -1),  # Target greater than all elements
        (numbers, 0, -1),   # Target smaller than all elements
        ([], 5, -1),        # Empty list
        ([42], 42, 0),      # Single element, found
        ([42], 7, -1),      # Single element, not found
    ]
    
    print("Binary Search Test Results:")
    print("=" * 40)
    
    for i, (test_list, target, expected) in enumerate(test_cases, 1):
        try:
            result = binary_search(test_list, target)
            status = "✓ PASS" if result == expected else "✗ FAIL"
            print(f"Test {i:2d}: Target={target:2d}, Expected={expected:2d}, Got={result:2d} {status}")
        except Exception as e:
            print(f"Test {i:2d}: Target={target:2d}, Error: {e}")
    
    # Test with strings
    print("\nString List Test:")
    print("=" * 40)
    words = ["apple", "banana", "cherry", "date", "elderberry", "fig", "grape"]
    string_tests = [
        (words, "cherry", 2),
        (words, "apple", 0),
        (words, "grape", 6),
        (words, "orange", -1),
    ]
    
    for i, (test_list, target, expected) in enumerate(string_tests, 1):
        result = binary_search(test_list, target)
        status = "✓ PASS" if result == expected else "✗ FAIL"
        print(f"String Test {i}: Target='{target}', Expected={expected}, Got={result} {status}")
    
    # Demonstrate error handling
    print("\nError Handling Test:")
    print("=" * 40)
    try:
        unsorted_list = [3, 1, 4, 1, 5]
        binary_search(unsorted_list, 4)
    except ValueError as e:
        print(f"✓ Correctly caught unsorted list error: {e}")
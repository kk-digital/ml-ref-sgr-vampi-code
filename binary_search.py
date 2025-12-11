from typing import List, Any


def binary_search(sorted_list: List[Any], target: Any) -> int:
    """
    Perform binary search on a sorted list to find the target value.
    
    Binary search is an efficient algorithm for finding an item from a sorted list.
    It works by repeatedly dividing the search interval in half. If the target value
    is less than the middle element, the search continues in the lower half, otherwise
    in the upper half. This process continues until the target is found or the interval
    is empty.
    
    Time Complexity: O(log n)
    Space Complexity: O(1)
    
    Args:
        sorted_list: A list sorted in ascending order. Elements must be comparable.
        target: The value to search for in the list.
    
    Returns:
        The index of the target value if found in the list.
        Returns -1 if the target is not found.
    
    Examples:
        >>> binary_search([1, 2, 3, 4, 5, 6, 7, 8, 9], 5)
        4
        >>> binary_search([1, 2, 3, 4, 5], 10)
        -1
        >>> binary_search([], 1)
        -1
        >>> binary_search([1], 1)
        0
    """
    left = 0
    right = len(sorted_list) - 1
    
    while left <= right:
        # Calculate middle index (avoiding potential overflow)
        mid = left + (right - left) // 2
        
        # Check if target is at middle
        if sorted_list[mid] == target:
            return mid
        
        # If target is greater, ignore left half
        elif sorted_list[mid] < target:
            left = mid + 1
        
        # If target is smaller, ignore right half
        else:
            right = mid - 1
    
    # Target was not found
    return -1


# Example usage and testing
if __name__ == "__main__":
    # Test cases
    test_list = [1, 3, 5, 7, 9, 11, 13, 15, 17, 19]
    
    print("Test List:", test_list)
    print()
    
    # Test 1: Find existing element
    target1 = 7
    result1 = binary_search(test_list, target1)
    print(f"Searching for {target1}: Found at index {result1}")
    
    # Test 2: Find first element
    target2 = 1
    result2 = binary_search(test_list, target2)
    print(f"Searching for {target2}: Found at index {result2}")
    
    # Test 3: Find last element
    target3 = 19
    result3 = binary_search(test_list, target3)
    print(f"Searching for {target3}: Found at index {result3}")
    
    # Test 4: Element not in list
    target4 = 8
    result4 = binary_search(test_list, target4)
    print(f"Searching for {target4}: Found at index {result4}")
    
    # Test 5: Empty list
    empty_list = []
    target5 = 5
    result5 = binary_search(empty_list, target5)
    print(f"Searching for {target5} in empty list: Found at index {result5}")
    
    # Test 6: Single element list (found)
    single_list = [42]
    target6 = 42
    result6 = binary_search(single_list, target6)
    print(f"Searching for {target6} in {single_list}: Found at index {result6}")
    
    # Test 7: Single element list (not found)
    target7 = 10
    result7 = binary_search(single_list, target7)
    print(f"Searching for {target7} in {single_list}: Found at index {result7}")

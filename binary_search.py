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
        sorted_list: A list of comparable elements sorted in ascending order.
        target: The value to search for in the list.
    
    Returns:
        The index of the target value if found, otherwise -1.
    
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
        # Calculate middle index (avoids potential overflow)
        mid = left + (right - left) // 2
        
        # Check if target is at mid
        if sorted_list[mid] == target:
            return mid
        
        # If target is greater, ignore left half
        elif sorted_list[mid] < target:
            left = mid + 1
        
        # If target is smaller, ignore right half
        else:
            right = mid - 1
    
    # Target not found
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
    print(f"Searching for {target1}: Index = {result1}")
    
    # Test 2: Find element at the beginning
    target2 = 1
    result2 = binary_search(test_list, target2)
    print(f"Searching for {target2}: Index = {result2}")
    
    # Test 3: Find element at the end
    target3 = 19
    result3 = binary_search(test_list, target3)
    print(f"Searching for {target3}: Index = {result3}")
    
    # Test 4: Element not in list
    target4 = 8
    result4 = binary_search(test_list, target4)
    print(f"Searching for {target4}: Index = {result4}")
    
    # Test 5: Empty list
    result5 = binary_search([], 5)
    print(f"Searching in empty list: Index = {result5}")
    
    # Test 6: Single element list (found)
    result6 = binary_search([5], 5)
    print(f"Searching in single element list (found): Index = {result6}")
    
    # Test 7: Single element list (not found)
    result7 = binary_search([5], 3)
    print(f"Searching in single element list (not found): Index = {result7}")

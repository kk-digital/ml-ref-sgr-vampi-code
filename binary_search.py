from typing import List


def binary_search(sorted_list: List[int], target: int) -> int:
    """
    Perform binary search on a sorted list to find the target value.
    
    Binary search is an efficient algorithm for finding an item from a sorted list.
    It works by repeatedly dividing the search interval in half. If the target value
    is less than the middle element, the search continues in the lower half, otherwise
    it continues in the upper half. This process continues until the target is found
    or the search interval is empty.
    
    Time Complexity: O(log n)
    Space Complexity: O(1)
    
    Args:
        sorted_list: A list of integers sorted in ascending order.
        target: The integer value to search for in the list.
    
    Returns:
        The index of the target value if found, or -1 if the target is not in the list.
    
    Examples:
        >>> binary_search([1, 2, 3, 4, 5, 6, 7, 8, 9], 5)
        4
        >>> binary_search([1, 2, 3, 4, 5, 6, 7, 8, 9], 10)
        -1
        >>> binary_search([1, 3, 5, 7, 9], 1)
        0
        >>> binary_search([1, 3, 5, 7, 9], 9)
        4
        >>> binary_search([], 5)
        -1
    """
    left = 0
    right = len(sorted_list) - 1
    
    while left <= right:
        # Calculate middle index (avoiding potential overflow)
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
    
    # Target was not found
    return -1


# Example usage and testing
if __name__ == "__main__":
    # Test cases
    test_list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    
    print("Test List:", test_list)
    print(f"Search for 5: Index = {binary_search(test_list, 5)}")  # Expected: 4
    print(f"Search for 1: Index = {binary_search(test_list, 1)}")  # Expected: 0
    print(f"Search for 10: Index = {binary_search(test_list, 10)}")  # Expected: 9
    print(f"Search for 11: Index = {binary_search(test_list, 11)}")  # Expected: -1
    print(f"Search for 0: Index = {binary_search(test_list, 0)}")  # Expected: -1
    
    # Edge cases
    print("\nEdge Cases:")
    print(f"Empty list: {binary_search([], 5)}")  # Expected: -1
    print(f"Single element (found): {binary_search([5], 5)}")  # Expected: 0
    print(f"Single element (not found): {binary_search([5], 3)}")  # Expected: -1

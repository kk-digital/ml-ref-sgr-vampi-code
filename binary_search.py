from typing import List, Any


def binary_search(sorted_list: List[Any], target: Any) -> int:
    """
    Perform binary search on a sorted list to find the target value.
    
    Args:
        sorted_list (List[Any]): A list that must be sorted in ascending order.
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
    # Verify that the list is sorted (optional but helpful for debugging)
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
    
    print("Testing binary search with integers:")
    print(f"List: {numbers}")
    print(f"Search for 7: {binary_search(numbers, 7)}")  # Expected: 3
    print(f"Search for 1: {binary_search(numbers, 1)}")  # Expected: 0
    print(f"Search for 19: {binary_search(numbers, 19)}")  # Expected: 9
    print(f"Search for 8: {binary_search(numbers, 8)}")  # Expected: -1
    
    # Test with strings
    words = ["apple", "banana", "cherry", "date", "fig", "grape"]
    
    print("\nTesting binary search with strings:")
    print(f"List: {words}")
    print(f"Search for 'cherry': {binary_search(words, 'cherry')}")  # Expected: 2
    print(f"Search for 'apple': {binary_search(words, 'apple')}")  # Expected: 0
    print(f"Search for 'grape': {binary_search(words, 'grape')}")  # Expected: 5
    print(f"Search for 'orange': {binary_search(words, 'orange')}")  # Expected: -1
    
    # Test with empty list
    print(f"\nSearch in empty list: {binary_search([], 5)}")  # Expected: -1
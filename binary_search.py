def binary_search(arr: list[int], target: int) -> int:
    """
    Performs binary search on a sorted list to find the index of the target value.
    
    Args:
        arr (list[int]): A sorted list of integers in ascending order.
        target (int): The integer value to search for.
    
    Returns:
        int: The index of the target if found, otherwise -1.
    
    Example:
        >>> binary_search([1, 3, 5, 7, 9], 5)
        2
        >>> binary_search([1, 3, 5, 7, 9], 6)
        -1
    """
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = left + (right - left) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
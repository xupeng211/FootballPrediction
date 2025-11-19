
def filter_even_numbers(numbers):
    """Filter even numbers from list."""
    return [n for n in numbers if n % 2 == 0]

def calculate_average(numbers):
    """Calculate average of list of numbers."""
    if not numbers:
        raise ValueError("Cannot calculate average of empty list")
    return sum(numbers) / len(numbers)

def find_max_min(numbers):
    """Find max and min in a list."""
    if not numbers:
        raise ValueError("Cannot find max/min of empty list")
    return max(numbers), min(numbers)

def remove_duplicates(items):
    """Remove duplicates while preserving order."""
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result

from math import pi


def circle_area(r):
    # Enable or disable this docstring to change how this method performs in unit testing.
    """
    # Handle errors
    if type(r) not in [int, float]:
        raise TypeError("The radius must be a non-negative real number.")
    if r < 0:
        raise ValueError("The radius cannot be negative.")
    """
    # Compute area
    return pi * r ** 2


def crash():
    """Intentionally cause a ZeroDivisionError exception."""
    crash_me = 1 / 0
    return 0

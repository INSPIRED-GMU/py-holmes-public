"""Dummy method for use in certain tests in test_py_holmes.py.
"""


from comma_imports_imported import my_sin, my_cos, my_tan


def compute():
    """Use imports my_sin, my_cos, and my_tan"""
    return my_sin(my_cos(my_tan(1)))

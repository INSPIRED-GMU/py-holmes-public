"""Classes and functions for stripping unwanted characters and substrings from strings."""


def strip_custom(input_string: str, chars_to_remove, head_or_tail: str) -> str:
    """Strip all characters from chars_to_remove from either the head or tail of input_string.
    Stop when the first character not in chars_to_remove is encountered.
    chars_to_remove is a list of strings where each string has length 1
    """
    # Handle errors
    # input_string not a string
    if not isinstance(input_string, str):
        raise TypeError("input_string must be a string")
    # chars_to_remove not a list
    if not isinstance(chars_to_remove, list):
        raise TypeError("chars_to_remove must be a list")
    # Incorrect datatype in chars_to_remove
    for entry in chars_to_remove:
        if not isinstance(entry, str):
            raise TypeError("All entries in chars_to_remove must be strings")
    # Incorrect string length in chars_to_remove
    for entry in chars_to_remove:
        if len(entry) != 1:
            raise ValueError("All strings in chars_to_remove must have length 1")
    # head_or_tail does not equal "head" or "tail"
    if head_or_tail not in ["head", "tail"]:
        raise TypeError("head_or_tail must be either string 'head' or string 'tail'")

    # Strip characters
    if head_or_tail == "head":
        removal_index = 0
    else:   # head_or_tail must == "tail"
        removal_index = -1
    while len(input_string) > 0 and input_string[removal_index] in chars_to_remove:
        if head_or_tail == "head":
            input_string = input_string[1:]
        else:   # head_or_tail must == "tail"
            input_string = input_string[:-1]
    return input_string


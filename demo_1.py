"""Source code used as an example in demo paper 1.
"""


def word_to_int(s: str) -> int:
    """Given a word, return an integer unique to that string.
    Only accepts lowercase strings without spaces.
    A word with more letters in the range a-z will always have a larger integer than a word with
    fewer letters.
    If two words have the same number of letters a-z, then the leftmost differing character pair
    will determine which word is greater.  The word whose differing letter is later in the alphabet
    will be greater.
    Evaluation is similar to finding the value of a base-27 number, except there is no digit for 0.
    Example outputs:
    "a"     ->      1
    "z"     ->      26
    "aa"    ->      27
    "ba"    ->      53
    "foo"   ->      4461
    """
    # Enforce preconditions
    # s must not contain a space
    if " " in s:
        raise ValueError("s must not contain a space")
    # s must be all-lowercase
    if s.lower() != s:
        raise ValueError("s must be all-lowercase")

    permitted_chars = "abcdefghijklmnopqrstuvwxyz"
    total = 0
    for ii in range(len(s)):
        char = s[ii]
        if char in permitted_chars:
            pos_in_perm = permitted_chars.index(char)
            total += (pos_in_perm + 1) * len(permitted_chars)**(len(s)-ii-1)
    return total

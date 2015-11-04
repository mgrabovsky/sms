import difflib

def diff_strings(old, new):
    return difflib.unified_diff(old, new, 'before', 'after')


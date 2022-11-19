"""Classes and functions for importing modules and packages."""


from importlib import import_module
from ph_basic_processing.parsers import concatenate_list_to_string


def import_by_string(path: str):
    """Given a path string, import the module or class, and return it.
    References this StackOverflow thread: https://stackoverflow.com/questions/547829/how-to-dynamically-load-a-python-class
    """
    # Handle errors
    # path not a string
    if not isinstance(path, str):
        raise TypeError("path must be a string")
    # path empty
    if len(path) == 0:
        raise ValueError("path must not be empty")

    # Change path to correct format
    path_preprocessed = ""
    for word in path.split(" "):
        if word not in ["from", "import"]:
            path_preprocessed += word + "."
    if path_preprocessed.endswith("."):
        path_preprocessed = path_preprocessed[:-1]
    path = path_preprocessed
    del path_preprocessed

    # The original technique from the StackOverflow thread, but it can't handle the "/" symbol, such as for directories:
    #components = path.split(".")
    #mod = __import__(components[0])
    #for this_component in components[1:]:
        #mod = getattr(mod, this_component)
    #return mod

    # Our technique, which allows for imports of files in deeper folders:
    if "." in path:     # path contains more than one component; this is a more complicated import
        components = path.split(".")
        mod = import_module(concatenate_list_to_string(components[0:-1], "."))  # Get the module represented by path sans whatever follows the final period
        mod = getattr(mod, components[-1])  # Import whatever follows the final period using what came before
        return mod
    else:   # path contains only one component; this is a simpler import
        mod = __import__(path)
        return mod

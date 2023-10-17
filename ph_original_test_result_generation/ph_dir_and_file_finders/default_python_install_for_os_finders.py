"""Classes and functions to find the default Python install location for the user's operating system."""


#
# IMPORTS
#
from os import walk, path, environ
from sys import platform, version_info


#
# HELPER FUNCTIONS
#
def get_python_path_for_platform() -> str:
    """Return the absolute filepath of the default install location for Python on the user's operating system."""
    if platform in ["win32", "win64"]:  # Windows
        return environ["USERPROFILE"] + "\\AppData\\Local\\Programs\\Python"

    elif platform == "darwin":  # macOS
        for _this_root_dir in ["/usr/local/Cellar", "/usr/bin", "/usr/local/bin"]:
            _immediate_child_directories = next(walk(_this_root_dir))[1]
            if "python" in _immediate_child_directories:
                return path.join(_this_root_dir, "python")

    elif platform == "linux":   # Linux
        return f"/usr/lib/python{version_info[0]}.{version_info[1]}"    # eg /usr/lib/python3.8

    else:
        raise RuntimeError("Unfamiliar operating system. Don't know the default install location for Python for this OS.  Try using Linux, macOS, or Windows instead.")

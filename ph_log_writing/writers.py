"""Classes and functions for redirecting output streams to log files."""


import sys


class writer(object):
    """For use during testing of py_holmes itself.  Replaces sys.stdout and sys.stderr stream objects, so that
    everything that gets displayed on the console also goes to a log file.
    """
    global _fh
    global _orig_stdout
    _fh = None
    _orig_stdout = sys.stdout

    def __init__(self):
        global _fh
        global _orig_stdout
        _fh = open("log_from_most_recent_run.log", "w", encoding="utf-8")

    def write(self, data):
        global _fh
        global _orig_stdout
        _fh.write(data)
        _orig_stdout.write(data)

    def flush(self):
        global _fh
        global _orig_stdout
        _orig_stdout.flush()

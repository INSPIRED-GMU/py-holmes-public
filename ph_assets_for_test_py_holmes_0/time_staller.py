"""For use by test_py_holmes.py"""


from time import sleep


def stall_for_time() -> None:
    """Sleep for some amount of time.
    :param duration:        how many seconds to sleep for
    """
    sleep(1)

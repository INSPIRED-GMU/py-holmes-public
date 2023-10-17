"""Allows for manual inspection of the get_call_from_traceback_test() function of py_holmes.py.
No automated oracle is currently implemented.
"""

import json
from ph_basic_processing.parsers import get_call_from_traceback
import random

random.seed(10)

# Get list of tracebacks
json_filename = "ph_traceback_dataset/stacktraces.json"
json_file = open(json_filename, "r", encoding="utf-8")
try:
    data = json.load(json_file)
    tracebacks = [data["data"][ii][3] for ii in range(len(data["data"]))]
finally:
    json_file.close()

# For count random tracebacks in the list, print what get_call_from_traceback() thinks the call is
tts_used = []
for count in range(100):
    tt = random.randint(0, len(tracebacks)-1)
    while tt in tts_used:
        tt = random.randint(0, len(tracebacks) - 1)
    tts_used.append(tt)
    this_traceback = tracebacks[tt]
    print("\nCOUNT == " + str(count))
    print("CALL FOR tt == " + str(tt) + ":")
    if tt in [34, 40, 46, 52, 66, 67, 228605, 273603, 346998] or this_traceback in ["Traceback (most recent call last):...", "Traceback (most recent call last):\r```\r"]:
        print("IGNORED: WREN VERIFIED NO CALL TO SEE")
    elif tt in [33, 35, 17083, 102211, 272980, 349537] or this_traceback in []:
        print("IGNORED: WREN VERIFIED TRACEBACK TOO LOW-QUALITY FOR REALISTIC EXTRACTION")
    else:
        print("ORIGINAL TRACEBACK:\n" + repr(this_traceback))
        print("EXTRACTED CALL:\n" + repr(get_call_from_traceback(this_traceback)))
print("Done!")

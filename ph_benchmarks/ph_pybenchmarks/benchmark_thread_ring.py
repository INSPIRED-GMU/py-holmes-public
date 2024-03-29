# The Computer Language Benchmarks Game
# http://benchmarksgame.alioth.debian.org/
# Contributed by Antti Kervinen
# Modified by Tupteq
# 2to3

import sys
import _thread

# Set minimum stack size for threads, otherwise the program may fail
# to create such a many threads
_thread.stack_size(32*1024)

def threadfun(number, lock_acquire, next_release):
    global n
    while 1:
        lock_acquire()
        if n > 0:
            n -= 1
            next_release()
        else:
            print(number)
            main_lock.release()

# main
n = int(sys.argv[1])
main_lock = _thread.allocate_lock()
main_lock.acquire()

first_lock = _thread.allocate_lock()
next_lock = first_lock

for number in range(503):
    lock = next_lock
    lock.acquire()
    next_lock = _thread.allocate_lock() if number < 502 else first_lock
    _thread.start_new_thread(threadfun,
        (number+1, lock.acquire, next_lock.release))

first_lock.release()
main_lock.acquire()
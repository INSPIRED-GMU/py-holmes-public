# The Computer Language Benchmarks Game
# http://benchmarksgame.alioth.debian.org/
# contributed by Daniel Nanz 2008-04-10
# 2to3

import sys
import _thread
import time

# colors and matching
creature_colors = ['blue', 'red', 'yellow']


def complement(c1, c2):
    if c1 == c2: return c1
    if c1 == 'blue':
        if c2 == 'red': return 'yellow'
        return 'red'
    if c1 == 'red':
        if c2 == 'blue': return 'yellow'
        return 'blue'
    if c2 == 'blue': return 'red'
    return 'blue'


compl_dict = dict(((c1, c2), complement(c1, c2))
                  for c1 in creature_colors
                  for c2 in creature_colors)


def check_complement(colors=creature_colors, compl=compl_dict):
    for c1 in colors:
        for c2 in colors:
            print('%s + %s -> %s' % (c1, c2, compl[(c1, c2)]))
    print('')


# reporting
def spellout(n):
    numbers = ['zero', 'one', 'two', 'three', 'four',
               'five', 'six', 'seven', 'eight', 'nine']
    return ' ' + ' '.join(numbers[int(c)] for c in str(n))


def report(input_zoo, met, self_met):
    print(' ' + ' '.join(input_zoo))
    for m, sm in zip(met, self_met):
        print(str(m) + spellout(sm))
    print(spellout(sum(met)) + '\n')


# the zoo
def creature(my_id, venue, my_lock_acquire, in_lock_acquire, out_lock_release):
    while True:
        my_lock_acquire()  # only proceed if not already at meeting place
        in_lock_acquire()  # only proceed when holding in_lock
        venue[0] = my_id  # register at meeting place
        out_lock_release()  # signal "registration ok"


def let_them_meet(meetings_left, input_zoo,
                  compl=compl_dict, allocate=_thread.allocate_lock):
    # prepare
    c_no = len(input_zoo)
    venue = [-1]
    met = [0] * c_no
    self_met = [0] * c_no
    colors = input_zoo[:]

    in_lock = allocate()
    in_lock_acquire = in_lock.acquire  # function aliases
    in_lock_release = in_lock.release  # (minor performance gain)
    in_lock_acquire()
    out_lock = allocate()
    out_lock_release = out_lock.release
    out_lock_acquire = out_lock.acquire
    out_lock_acquire()
    locks = [allocate() for c in input_zoo]

    # let creatures wild
    for ci in range(c_no):
        args = (ci, venue, locks[ci].acquire, in_lock_acquire, out_lock_release)
        new = _thread.start_new_thread(creature, args)
    time.sleep(0.05)  # to reduce work-load imbalance

    in_lock_release()  # signal "meeting_place open for registration"
    out_lock_acquire()  # only proceed with a "registration ok" signal
    id1 = venue[0]
    while meetings_left > 0:
        in_lock_release()
        out_lock_acquire()
        id2 = venue[0]
        if id1 != id2:
            new_color = compl[(colors[id1], colors[id2])]
            colors[id1] = new_color
            colors[id2] = new_color
            met[id1] += 1
            met[id2] += 1
        else:
            self_met[id1] += 1
            met[id1] += 1
        meetings_left -= 1
        if meetings_left > 0:
            locks[id1].release()  # signal "you were kicked from meeting place"
            id1 = id2
        else:
            report(input_zoo, met, self_met)


def chameneosiate(n):
    check_complement()
    let_them_meet(n, ['blue', 'red', 'yellow'])
    let_them_meet(n, ['blue', 'red', 'yellow', 'red', 'yellow',
                      'blue', 'red', 'yellow', 'red', 'blue'])
    # print ''


chameneosiate(int(sys.argv[1]))
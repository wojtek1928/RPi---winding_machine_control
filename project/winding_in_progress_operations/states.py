from enum import Enum


class STATES(Enum):
    """
    - working
    - paused
    - cancelling
    - done
    - end
    """
    paused = 1
    cancel = 2
    working = 3
    working_fail = 4
    cut_rope = 5
    cut_rope_fail = 6
    reset_position = 7
    reset_position_fail = 8
    next_run_confirmation = 9
    next_rope = 10
    summary = 11
    finish = 12

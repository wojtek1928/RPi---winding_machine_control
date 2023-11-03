from enum import Enum, auto


class STATES(Enum):
    """
    - paused
    - cancel
    - winding
    - winding_fail
    - cut_rope
    - cut_rope_fail
    - reset_position
    - reset_position_fail
    - next_run_confirmation
    - next_rope
    - summary
    """
    paused = auto()
    cancel = auto()
    winding = auto()
    winding_fail = auto()
    cut_rope = auto()
    cut_rope_fail = auto()
    reset_position = auto()
    reset_position_fail = auto()
    next_run_confirmation = auto()
    next_rope = auto()
    summary = auto()

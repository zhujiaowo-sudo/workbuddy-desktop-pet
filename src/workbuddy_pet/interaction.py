"""Local click responses; independent of WorkBuddy task events and approvals."""
from dataclasses import dataclass
import random

from .materials import LEISURE_ACTIONS


@dataclass(frozen=True)
class Interaction:
    text: str
    action: str
    seconds: float = 3.2


RESPONSES=(
    Interaction('摸摸头收到啦，挥挥手一起加油！','click_wave'),
    Interaction('给你比心，今天也要元气满满～','click_heart'),
    Interaction('嘿嘿，被你发现我在陪着你啦','click_shy'),
    Interaction('哇！收到你的能量补给啦！','click_surprised'),
)


def response_for_click(index):return RESPONSES[index%len(RESPONSES)]


def idle_allowed(sessions, display, wall_time):
    """All sessions count; a finished foreground task cannot hide a busy peer."""
    if display.state not in ('idle', 'done'):
        return False
    for session in sessions.values():
        if session.state not in ('idle', 'done'):
            return False
        if session.state == 'done' and wall_time - session.at < 12:
            return False
    return True


class IdleDirector:
    """Monotonic local scheduling, with an injectable random source for tests."""
    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.next_due = None
        self.active = None
        self.until = 0
        self.previous = None

    def cancel(self):
        self.active = None
        self.next_due = None
        self.until = 0

    def step(self, now, eligible):
        if not eligible:
            self.cancel()
            return None
        if self.active and now < self.until:
            return self.active
        if self.active:
            self.active = None
            self.next_due = now + self.rng.uniform(45, 110)
        if self.next_due is None:
            self.next_due = now + self.rng.uniform(45, 110)
        if now >= self.next_due:
            action = self.rng.choice([a for a in LEISURE_ACTIONS if a != self.previous])
            self.active = Interaction('', action, self.rng.uniform(6, 10))
            self.previous = action
            self.until = now + self.active.seconds
            return self.active
        return None

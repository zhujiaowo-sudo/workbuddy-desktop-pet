"""Local click responses; independent of WorkBuddy task events and approvals."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Interaction:
    text: str
    action: str
    seconds: float = 4


RESPONSES=(
    Interaction('摸摸头收到啦，一起加油！','done'),
    Interaction('在呢，陪你把事情做好～','waiting'),
    Interaction('举手！今天也要元气满满','done'),
    Interaction('给你比心，忙完记得休息','idle'),
)


def response_for_click(index):return RESPONSES[index%len(RESPONSES)]

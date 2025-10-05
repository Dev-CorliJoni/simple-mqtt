from enum import IntEnum


class RetainHandling(IntEnum):
    # broker sends retained messages on every subscribe
    SendRetainedAlways = 0
    # broker sends retained messages only on a new subscription
    SendRetainedOnNewSubscription = 1
    # broker never sends retained messages for this subscription
    DoNotSendRetained = 2

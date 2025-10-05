from enum import IntEnum


class QualityOfService(IntEnum):
    AtMostOnce = 0
    AtLeastOnce = 1
    ExactlyOnce = 2

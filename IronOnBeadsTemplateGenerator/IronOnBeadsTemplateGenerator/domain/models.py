from enum import Enum

class SupportedThresholdMethod(Enum):
    CUSTOM = 1
    LI = 2
    NIBLACK = 3
    SAUVOLA = 4
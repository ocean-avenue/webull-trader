UNKNOWN = 'Unknown'


class ActionType:
    BUY = 0
    SELL = 1

    @staticmethod
    def tostr(val):
        if val == ActionType.BUY:
            return 'BUY'
        if val == ActionType.SELL:
            return 'SELL'
        return UNKNOWN


class OrderType:
    LMT = 0
    MKT = 1
    STP = 2
    STP_LMT = 3
    STP_TRAIL = 4

    @staticmethod
    def tostr(val):
        if val == OrderType.LMT:
            return 'LMT'
        if val == OrderType.MKT:
            return 'MKT'
        if val == OrderType.STP:
            return 'STP'
        if val == OrderType.STP_LMT:
            return 'STP LMT'
        if val == OrderType.STP_TRAIL:
            return 'STP TRAIL'
        return UNKNOWN


class StatusType:
    FILLED = 0
    CANCELLED = 1
    PARTIALLY_FILLED = 2
    FAILED = 3
    WORKING = 4
    PENDING = 5

    @staticmethod
    def tostr(val):
        if val == StatusType.FILLED:
            return 'FILLED'
        if val == StatusType.CANCELLED:
            return 'CANCELLED'
        if val == StatusType.PARTIALLY_FILLED:
            return 'PARTIALLY_FILLED'
        if val == StatusType.FAILED:
            return 'FAILED'
        if val == StatusType.WORKING:
            return 'WORKING'
        if val == StatusType.PENDING:
            return 'PENDING'
        return UNKNOWN


class TimeInForceType:
    GTC = 0
    DAY = 1
    IOC = 2

    @staticmethod
    def tostr(val):
        if val == TimeInForceType.GTC:
            return 'GTC'
        if val == TimeInForceType.DAY:
            return 'DAY'
        if val == TimeInForceType.IOC:
            return 'IOC'
        return UNKNOWN

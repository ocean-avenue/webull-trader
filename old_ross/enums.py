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


class SetupType:
    DAY_FIRST_CANDLE_NEW_HIGH = 0
    DAY_GAP_AND_GO = 1
    DAY_BULL_FLAG = 2
    DAY_REVERSAL = 3
    SWING_20_DAYS_NEW_HIGH = 4

    @staticmethod
    def tostr(val):
        if val == SetupType.DAY_FIRST_CANDLE_NEW_HIGH:
            return '(Day) First candle new high'
        if val == SetupType.DAY_GAP_AND_GO:
            return '(Day) Gap and Go'
        if val == SetupType.DAY_BULL_FLAG:
            return '(Day) Bull Flag'
        if val == SetupType.DAY_REVERSAL:
            return '(Day) Reversal'
        if val == SetupType.SWING_20_DAYS_NEW_HIGH:
            return '(Swing) 20 days new high'
        return UNKNOWN

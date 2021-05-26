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
    DAY_RED_TO_GREEN = 4
    SWING_20_DAYS_NEW_HIGH = 100
    SWING_55_DAYS_NEW_HIGH = 101

    @staticmethod
    def tostr(val):
        if val == SetupType.DAY_FIRST_CANDLE_NEW_HIGH:
            return '[Day] First candle new high'
        if val == SetupType.DAY_GAP_AND_GO:
            return '[Day] Gap and Go'
        if val == SetupType.DAY_BULL_FLAG:
            return '[Day] Bull Flag'
        if val == SetupType.DAY_REVERSAL:
            return '[Day] Reversal'
        if val == SetupType.DAY_RED_TO_GREEN:
            return '[Day] Red to Green'
        if val == SetupType.SWING_20_DAYS_NEW_HIGH:
            return '[Swing] 20 days new high'
        if val == SetupType.SWING_55_DAYS_NEW_HIGH:
            return '[Swing] 55 days new high'
        return UNKNOWN


class AlgorithmType:
    DAY_MOMENTUM = 0
    DAY_MOMENTUM_REDUCE_SIZE = 1
    DAY_RED_TO_GREEN = 2
    SWING_TURTLE_20 = 100
    SWING_TURTLE_55 = 101
    LIVE = 200

    @staticmethod
    def tostr(val):
        return '[{}] {}'.format(AlgorithmType.totag(val), AlgorithmType.todesc(val))

    @staticmethod
    def todesc(val):
        if val == AlgorithmType.DAY_MOMENTUM:
            return 'Momo day trade as much as possible, mainly for collect data.'
        if val == AlgorithmType.DAY_MOMENTUM_REDUCE_SIZE:
            return 'Momo day trade based on win rate, reduce size when win rate low.'
        if val == AlgorithmType.DAY_RED_TO_GREEN:
            return 'Day trade based on red to green strategy.'
        if val == AlgorithmType.SWING_TURTLE_20:
            return 'Swing trade based on turtle trading rules (20 days).'
        if val == AlgorithmType.SWING_TURTLE_55:
            return 'Swing trade based on turtle trading rules (55 days).'
        if val == AlgorithmType.LIVE:
            return 'Live day/swing trade based on history statistics data.'
        return UNKNOWN

    @staticmethod
    def totag(val):
        if val == AlgorithmType.DAY_MOMENTUM:
            return 'DAY/MOMO'
        if val == AlgorithmType.DAY_MOMENTUM_REDUCE_SIZE:
            return 'DAY/MOMO REDUCE'
        if val == AlgorithmType.DAY_RED_TO_GREEN:
            return 'DAY/RED GREEN'
        if val == AlgorithmType.SWING_TURTLE_20:
            return 'SWING/TURTLE (20 DAYS)'
        if val == AlgorithmType.SWING_TURTLE_55:
            return 'SWING/TURTLE (55 DAYS)'
        if val == AlgorithmType.LIVE:
            return 'LIVE'
        return UNKNOWN

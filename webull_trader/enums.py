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

    @staticmethod
    def tochoices():
        return (
            (OrderType.LMT, OrderType.tostr(OrderType.LMT)),
            (OrderType.MKT, OrderType.tostr(OrderType.MKT)),
            (OrderType.STP, OrderType.tostr(OrderType.STP)),
            (OrderType.STP_LMT, OrderType.tostr(OrderType.STP_LMT)),
            (OrderType.STP_TRAIL, OrderType.tostr(OrderType.STP_TRAIL)),
        )


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

    @staticmethod
    def tochoices():
        return (
            (TimeInForceType.GTC, TimeInForceType.tostr(
                TimeInForceType.GTC)),
            (TimeInForceType.DAY, TimeInForceType.tostr(
                TimeInForceType.DAY)),
            (TimeInForceType.IOC, TimeInForceType.tostr(
                TimeInForceType.IOC)),
        )


class SetupType:
    DAY_FIRST_CANDLE_NEW_HIGH = 0
    DAY_GAP_AND_GO = 1
    DAY_BULL_FLAG = 2
    DAY_REVERSAL = 3
    DAY_RED_TO_GREEN = 4
    DAY_20_CANDLES_NEW_HIGH = 5
    DAY_30_CANDLES_NEW_HIGH = 6
    DAY_EARNINGS_GAP = 7
    DAY_10_CANDLES_NEW_HIGH = 8
    DAY_VWAP_RECLAIM = 9
    DAY_GRINDING_UP = 10
    SWING_20_DAYS_NEW_HIGH = 100
    SWING_55_DAYS_NEW_HIGH = 101
    ERROR_FAILED_TO_SELL = 500
    ERROR_FAILED_TO_CANCEL_ORDER = 501
    UNKNOWN = 999

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
        if val == SetupType.DAY_10_CANDLES_NEW_HIGH:
            return '[Day] 10 candles new high'
        if val == SetupType.DAY_20_CANDLES_NEW_HIGH:
            return '[Day] 20 candles new high'
        if val == SetupType.DAY_30_CANDLES_NEW_HIGH:
            return '[Day] 30 candles new high'
        if val == SetupType.DAY_EARNINGS_GAP:
            return '[Day] Earning Gap'
        if val == SetupType.DAY_VWAP_RECLAIM:
            return '[Day] VWAP Reclaim'
        if val == SetupType.DAY_GRINDING_UP:
            return '[Day] Grinding Up'
        if val == SetupType.SWING_20_DAYS_NEW_HIGH:
            return '[Swing] 20 days new high'
        if val == SetupType.SWING_55_DAYS_NEW_HIGH:
            return '[Swing] 55 days new high'
        if val == SetupType.ERROR_FAILED_TO_SELL:
            return '[Error] Failed to sell'
        if val == SetupType.ERROR_FAILED_TO_CANCEL_ORDER:
            return '[Error] Failed to cancel order'
        return UNKNOWN

    @staticmethod
    def tochoices():
        return (
            (SetupType.DAY_FIRST_CANDLE_NEW_HIGH, SetupType.tostr(
                SetupType.DAY_FIRST_CANDLE_NEW_HIGH)),
            (SetupType.DAY_GAP_AND_GO, SetupType.tostr(
                SetupType.DAY_GAP_AND_GO)),
            (SetupType.DAY_BULL_FLAG, SetupType.tostr(
                SetupType.DAY_BULL_FLAG)),
            (SetupType.DAY_REVERSAL, SetupType.tostr(
                SetupType.DAY_REVERSAL)),
            (SetupType.DAY_RED_TO_GREEN, SetupType.tostr(
                SetupType.DAY_RED_TO_GREEN)),
            (SetupType.DAY_10_CANDLES_NEW_HIGH, SetupType.tostr(
                SetupType.DAY_10_CANDLES_NEW_HIGH)),
            (SetupType.DAY_20_CANDLES_NEW_HIGH, SetupType.tostr(
                SetupType.DAY_20_CANDLES_NEW_HIGH)),
            (SetupType.DAY_30_CANDLES_NEW_HIGH, SetupType.tostr(
                SetupType.DAY_30_CANDLES_NEW_HIGH)),
            (SetupType.DAY_EARNINGS_GAP, SetupType.tostr(
                SetupType.DAY_EARNINGS_GAP)),
            (SetupType.DAY_VWAP_RECLAIM, SetupType.tostr(
                SetupType.DAY_VWAP_RECLAIM)),
            (SetupType.DAY_GRINDING_UP, SetupType.tostr(
                SetupType.DAY_GRINDING_UP)),
            (SetupType.SWING_20_DAYS_NEW_HIGH, SetupType.tostr(
                SetupType.SWING_20_DAYS_NEW_HIGH)),
            (SetupType.SWING_55_DAYS_NEW_HIGH, SetupType.tostr(
                SetupType.SWING_55_DAYS_NEW_HIGH)),
            (SetupType.ERROR_FAILED_TO_SELL, SetupType.tostr(
                SetupType.ERROR_FAILED_TO_SELL)),
            (SetupType.ERROR_FAILED_TO_CANCEL_ORDER, SetupType.tostr(
                SetupType.ERROR_FAILED_TO_CANCEL_ORDER)),
            (SetupType.UNKNOWN, SetupType.tostr(
                SetupType.UNKNOWN)),
        )


class AlgorithmType:
    DAY_MOMENTUM = 0
    DAY_MOMENTUM_REDUCE_SIZE = 1
    DAY_RED_TO_GREEN = 2
    DAY_MOMENTUM_NEW_HIGH = 3
    DAY_BREAKOUT_20 = 4
    DAY_BREAKOUT_30 = 5
    DAY_BREAKOUT_EARNINGS = 6
    DAY_EARNINGS = 7
    DAY_EARNINGS_OVERNIGHT = 8
    DAY_EARNINGS_BREAKOUT = 9
    # breakout entry with 10 candles new high
    DAY_BREAKOUT_10 = 10
    # breakout entry with 10 candles new high, only entry if price reach new high
    DAY_BREAKOUT_NEW_HIGH = 11
    # breakout entry with 10 candles new high (5min candle)
    DAY_BREAKOUT_10_5 = 12
    # breakout entry with 10 candles new high with pre day losers
    DAY_BREAKOUT_PRE_LOSERS = 13
    # breakout entry with 55 candles new high
    DAY_BREAKOUT_55 = 14
    DAY_VWAP_RECLAIM_LARGE_CAP = 15
    DAY_GRINDING_LARGE_CAP = 16
    DAY_GRINDING_SYMBOLS = 17
    # breakout entry with 20 candles new high, entry with ask price
    DAY_BREAKOUT_ASK = 18
    # breakout entry with 20 candles new high, 11 candles new low
    DAY_BREAKOUT_20_11 = 19
    # breakout entry with 20 candles new high, 9 candles new low
    DAY_BREAKOUT_20_9 = 20
    # breakout entry with 20 candles new high, 8 candles new low
    DAY_BREAKOUT_20_8 = 21
    # breakout entry with 20 candles new high with scale in
    DAY_BREAKOUT_SCALE = 22
    # breakout entry with 20 candles new high with period exit
    DAY_BREAKOUT_PERIOD = 23
    # breakout entry with 20 candles new high, 1 candles new low
    DAY_BREAKOUT_20_1 = 24
    # breakout entry with 20 candles new high with dynamic adjust exit
    DAY_BREAKOUT_DYNAMIC_EXIT = 25
    SWING_TURTLE_20 = 100
    SWING_TURTLE_55 = 101
    DAY_SWING_MOMO_TURTLE = 200
    DAY_SWING_RG_TURTLE = 201
    DAY_SWING_BREAKOUT_TURTLE = 202
    DAY_SWING_EARNINGS_TURTLE = 203

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
        if val == AlgorithmType.DAY_MOMENTUM_NEW_HIGH:
            return 'Momo day trade, no entry if the price not break max of last high trade price.'
        if val == AlgorithmType.DAY_BREAKOUT_10:
            return 'Breakout day trade, entry if price reach 10 candles new high.'
        if val == AlgorithmType.DAY_BREAKOUT_20:
            return 'Breakout day trade, entry if price reach 20 candles new high.'
        if val == AlgorithmType.DAY_BREAKOUT_30:
            return 'Breakout day trade, entry if price reach 30 candles new high.'
        if val == AlgorithmType.DAY_BREAKOUT_EARNINGS:
            return 'Breakout and earning day trade, entry if price reach period new high.'
        if val == AlgorithmType.DAY_BREAKOUT_NEW_HIGH:
            return 'Breakout day trade, no entry if the price not break max of last high trade price.'
        if val == AlgorithmType.DAY_BREAKOUT_10_5:
            return 'Breakout day trade, entry if price reach 10 candles new high in 5 minute chart.'
        if val == AlgorithmType.DAY_BREAKOUT_PRE_LOSERS:
            return 'Breakout day trade, find pre-market losers and aim for reversal.'
        if val == AlgorithmType.DAY_BREAKOUT_55:
            return 'Breakout day trade, entry if price reach 55 candles new high.'
        if val == AlgorithmType.DAY_EARNINGS:
            return 'Earning date day trade, entry if gap up and exit trade intraday.'
        if val == AlgorithmType.DAY_EARNINGS_OVERNIGHT:
            return 'Earning date day trade, entry if gap up and may hold position overnight.'
        if val == AlgorithmType.DAY_EARNINGS_BREAKOUT:
            return 'Earning date day trade, entry if gap up and do breakout trade if no earning event.'
        if val == AlgorithmType.DAY_VWAP_RECLAIM_LARGE_CAP:
            return 'VWAP reclaim day trade, entry if price reclaim vwap for large cap tickers.'
        if val == AlgorithmType.DAY_GRINDING_LARGE_CAP:
            return 'Grinding day trading with large cap and major news.'
        if val == AlgorithmType.DAY_GRINDING_SYMBOLS:
            return 'Grinding day trading with specific symbols.'
        if val == AlgorithmType.DAY_BREAKOUT_ASK:
            return 'Breakout day trade, entry with ask price limit order.'
        if val == AlgorithmType.DAY_BREAKOUT_20_11:
            return 'Breakout day trade, entry if price reach 20 candles new high, exit if price reach 11 candles new low.'
        if val == AlgorithmType.DAY_BREAKOUT_20_9:
            return 'Breakout day trade, entry if price reach 20 candles new high, exit if price reach 9 candles new low.'
        if val == AlgorithmType.DAY_BREAKOUT_20_8:
            return 'Breakout day trade, entry if price reach 20 candles new high, exit if price reach 8 candles new low.'
        if val == AlgorithmType.DAY_BREAKOUT_20_1:
            return 'Breakout day trade, entry if price reach 20 candles new high, exit if price reach 1 candles new low.'
        if val == AlgorithmType.DAY_BREAKOUT_SCALE:
            return 'Breakout day trade, entry if price reach 20 candles new high, scale in if reach add unit price.'
        if val == AlgorithmType.DAY_BREAKOUT_PERIOD:
            return 'Breakout day trade, entry if price reach 20 candles new high, exit if period time exceed.'
        if val == AlgorithmType.DAY_BREAKOUT_DYNAMIC_EXIT:
            return 'Breakout day trade, entry if price reach 20 candles new high, dynamic adjust exit period based on profit loss rate.'
        if val == AlgorithmType.SWING_TURTLE_20:
            return 'Swing trade based on turtle trading rules (20 days).'
        if val == AlgorithmType.SWING_TURTLE_55:
            return 'Swing trade based on turtle trading rules (55 days).'
        if val == AlgorithmType.DAY_SWING_MOMO_TURTLE:
            return '{} / {}'.format(AlgorithmType.todesc(AlgorithmType.DAY_MOMENTUM), AlgorithmType.todesc(AlgorithmType.SWING_TURTLE_55))
        if val == AlgorithmType.DAY_SWING_RG_TURTLE:
            return '{} / {}'.format(AlgorithmType.todesc(AlgorithmType.DAY_RED_TO_GREEN), AlgorithmType.todesc(AlgorithmType.SWING_TURTLE_55))
        if val == AlgorithmType.DAY_SWING_BREAKOUT_TURTLE:
            return '{} / {}'.format(AlgorithmType.todesc(AlgorithmType.DAY_BREAKOUT_10), AlgorithmType.todesc(AlgorithmType.SWING_TURTLE_55))
        if val == AlgorithmType.DAY_SWING_EARNINGS_TURTLE:
            return '{} / {}'.format(AlgorithmType.todesc(AlgorithmType.DAY_EARNINGS), AlgorithmType.todesc(AlgorithmType.SWING_TURTLE_55))
        return UNKNOWN

    @staticmethod
    def totag(val):
        if val == AlgorithmType.DAY_MOMENTUM:
            return 'DAY (MOMO)'
        if val == AlgorithmType.DAY_MOMENTUM_REDUCE_SIZE:
            return 'DAY (MOMO REDUCE SIZE)'
        if val == AlgorithmType.DAY_MOMENTUM_NEW_HIGH:
            return 'DAY (MOMO NEW HIGH)'
        if val == AlgorithmType.DAY_RED_TO_GREEN:
            return 'DAY (RED GREEN)'
        if val == AlgorithmType.DAY_BREAKOUT_10:
            return 'DAY (BREAKOUT 10)'
        if val == AlgorithmType.DAY_BREAKOUT_20:
            return 'DAY (BREAKOUT 20)'
        if val == AlgorithmType.DAY_BREAKOUT_30:
            return 'DAY (BREAKOUT 30)'
        if val == AlgorithmType.DAY_BREAKOUT_EARNINGS:
            return 'DAY (BREAKOUT EARNINGS)'
        if val == AlgorithmType.DAY_BREAKOUT_NEW_HIGH:
            return 'DAY (BREAKOUT NEW HIGH)'
        if val == AlgorithmType.DAY_BREAKOUT_10_5:
            return 'DAY (BREAKOUT 10-5)'
        if val == AlgorithmType.DAY_BREAKOUT_PRE_LOSERS:
            return 'DAY (BREAKOUT PRE LOSERS)'
        if val == AlgorithmType.DAY_BREAKOUT_55:
            return 'DAY (BREAKOUT 55)'
        if val == AlgorithmType.DAY_EARNINGS:
            return 'DAY (EARNINGS)'
        if val == AlgorithmType.DAY_EARNINGS_OVERNIGHT:
            return 'DAY (EARNINGS OVERNIGHT)'
        if val == AlgorithmType.DAY_EARNINGS_BREAKOUT:
            return 'DAY (EARNINGS BREAKOUT)'
        if val == AlgorithmType.DAY_VWAP_RECLAIM_LARGE_CAP:
            return 'DAY (VWAP LARGE CAP)'
        if val == AlgorithmType.DAY_GRINDING_LARGE_CAP:
            return 'DAY (GRINDING LARGE CAP)'
        if val == AlgorithmType.DAY_GRINDING_SYMBOLS:
            return 'DAY (GRINDING SYMBOLS)'
        if val == AlgorithmType.DAY_BREAKOUT_ASK:
            return 'DAY (BREAKOUT ASK)'
        if val == AlgorithmType.DAY_BREAKOUT_20_11:
            return 'DAY (BREAKOUT 20,11)'
        if val == AlgorithmType.DAY_BREAKOUT_20_9:
            return 'DAY (BREAKOUT 20,9)'
        if val == AlgorithmType.DAY_BREAKOUT_20_8:
            return 'DAY (BREAKOUT 20,8)'
        if val == AlgorithmType.DAY_BREAKOUT_20_1:
            return 'DAY (BREAKOUT 20,1)'
        if val == AlgorithmType.DAY_BREAKOUT_SCALE:
            return 'DAY (BREAKOUT SCALE)'
        if val == AlgorithmType.DAY_BREAKOUT_PERIOD:
            return 'DAY (BREAKOUT PERIOD)'
        if val == AlgorithmType.DAY_BREAKOUT_DYNAMIC_EXIT:
            return 'DAY (BREAKOUT DYN EXIT)'
        if val == AlgorithmType.SWING_TURTLE_20:
            return 'SWING (TURTLE 20)'
        if val == AlgorithmType.SWING_TURTLE_55:
            return 'SWING (TURTLE 55)'
        if val == AlgorithmType.DAY_SWING_MOMO_TURTLE:
            return '{} / {}'.format(AlgorithmType.totag(AlgorithmType.DAY_MOMENTUM), AlgorithmType.totag(AlgorithmType.SWING_TURTLE_55))
        if val == AlgorithmType.DAY_SWING_RG_TURTLE:
            return '{} / {}'.format(AlgorithmType.totag(AlgorithmType.DAY_RED_TO_GREEN), AlgorithmType.totag(AlgorithmType.SWING_TURTLE_55))
        if val == AlgorithmType.DAY_SWING_BREAKOUT_TURTLE:
            return '{} / {}'.format(AlgorithmType.totag(AlgorithmType.DAY_BREAKOUT_10), AlgorithmType.totag(AlgorithmType.SWING_TURTLE_55))
        if val == AlgorithmType.DAY_SWING_EARNINGS_TURTLE:
            return '{} / {}'.format(AlgorithmType.totag(AlgorithmType.DAY_EARNINGS), AlgorithmType.totag(AlgorithmType.SWING_TURTLE_55))
        return UNKNOWN

    @staticmethod
    def tochoices():
        return (
            (AlgorithmType.DAY_MOMENTUM, AlgorithmType.tostr(
                AlgorithmType.DAY_MOMENTUM)),
            (AlgorithmType.DAY_MOMENTUM_REDUCE_SIZE, AlgorithmType.tostr(
                AlgorithmType.DAY_MOMENTUM_REDUCE_SIZE)),
            (AlgorithmType.DAY_MOMENTUM_NEW_HIGH, AlgorithmType.tostr(
                AlgorithmType.DAY_MOMENTUM_NEW_HIGH)),
            (AlgorithmType.DAY_RED_TO_GREEN, AlgorithmType.tostr(
                AlgorithmType.DAY_RED_TO_GREEN)),
            (AlgorithmType.DAY_BREAKOUT_10, AlgorithmType.tostr(
                AlgorithmType.DAY_BREAKOUT_10)),
            (AlgorithmType.DAY_BREAKOUT_20, AlgorithmType.tostr(
                AlgorithmType.DAY_BREAKOUT_20)),
            (AlgorithmType.DAY_BREAKOUT_30, AlgorithmType.tostr(
                AlgorithmType.DAY_BREAKOUT_30)),
            (AlgorithmType.DAY_BREAKOUT_EARNINGS, AlgorithmType.tostr(
                AlgorithmType.DAY_BREAKOUT_EARNINGS)),
            (AlgorithmType.DAY_BREAKOUT_NEW_HIGH, AlgorithmType.tostr(
                AlgorithmType.DAY_BREAKOUT_NEW_HIGH)),
            (AlgorithmType.DAY_BREAKOUT_10_5, AlgorithmType.tostr(
                AlgorithmType.DAY_BREAKOUT_10_5)),
            (AlgorithmType.DAY_BREAKOUT_PRE_LOSERS, AlgorithmType.tostr(
                AlgorithmType.DAY_BREAKOUT_PRE_LOSERS)),
            (AlgorithmType.DAY_BREAKOUT_55, AlgorithmType.tostr(
                AlgorithmType.DAY_BREAKOUT_55)),
            (AlgorithmType.DAY_EARNINGS, AlgorithmType.tostr(
                AlgorithmType.DAY_EARNINGS)),
            (AlgorithmType.DAY_EARNINGS_OVERNIGHT, AlgorithmType.tostr(
                AlgorithmType.DAY_EARNINGS_OVERNIGHT)),
            (AlgorithmType.DAY_EARNINGS_BREAKOUT, AlgorithmType.tostr(
                AlgorithmType.DAY_EARNINGS_BREAKOUT)),
            (AlgorithmType.DAY_VWAP_RECLAIM_LARGE_CAP, AlgorithmType.tostr(
                AlgorithmType.DAY_VWAP_RECLAIM_LARGE_CAP)),
            (AlgorithmType.DAY_GRINDING_LARGE_CAP, AlgorithmType.tostr(
                AlgorithmType.DAY_GRINDING_LARGE_CAP)),
            (AlgorithmType.DAY_GRINDING_SYMBOLS, AlgorithmType.tostr(
                AlgorithmType.DAY_GRINDING_SYMBOLS)),
            (AlgorithmType.DAY_BREAKOUT_ASK, AlgorithmType.tostr(
                AlgorithmType.DAY_BREAKOUT_ASK)),
            (AlgorithmType.DAY_BREAKOUT_20_11, AlgorithmType.tostr(
                AlgorithmType.DAY_BREAKOUT_20_11)),
            (AlgorithmType.DAY_BREAKOUT_20_9, AlgorithmType.tostr(
                AlgorithmType.DAY_BREAKOUT_20_9)),
            (AlgorithmType.DAY_BREAKOUT_20_8, AlgorithmType.tostr(
                AlgorithmType.DAY_BREAKOUT_20_8)),
            (AlgorithmType.DAY_BREAKOUT_20_1, AlgorithmType.tostr(
                AlgorithmType.DAY_BREAKOUT_20_1)),
            (AlgorithmType.DAY_BREAKOUT_SCALE, AlgorithmType.tostr(
                AlgorithmType.DAY_BREAKOUT_SCALE)),
            (AlgorithmType.DAY_BREAKOUT_PERIOD, AlgorithmType.tostr(
                AlgorithmType.DAY_BREAKOUT_PERIOD)),
            (AlgorithmType.DAY_BREAKOUT_DYNAMIC_EXIT, AlgorithmType.tostr(
                AlgorithmType.DAY_BREAKOUT_DYNAMIC_EXIT)),
            (AlgorithmType.SWING_TURTLE_20, AlgorithmType.tostr(
                AlgorithmType.SWING_TURTLE_20)),
            (AlgorithmType.SWING_TURTLE_55, AlgorithmType.tostr(
                AlgorithmType.SWING_TURTLE_55)),
            (AlgorithmType.DAY_SWING_RG_TURTLE, AlgorithmType.tostr(
                AlgorithmType.DAY_SWING_RG_TURTLE)),
            (AlgorithmType.DAY_SWING_BREAKOUT_TURTLE, AlgorithmType.tostr(
                AlgorithmType.DAY_SWING_BREAKOUT_TURTLE)),
            (AlgorithmType.DAY_SWING_EARNINGS_TURTLE, AlgorithmType.tostr(
                AlgorithmType.DAY_SWING_EARNINGS_TURTLE)),
        )


class ScreenerType:
    MANUAL = 0
    EARNING_DAY = 1
    UNUSUAL_VOLUME = 2
    CHANNEL_UP = 3
    DOUBLE_BOTTOM = 4

    @staticmethod
    def tostr(val):
        if val == ScreenerType.MANUAL:
            return 'Manual'
        elif val == ScreenerType.EARNING_DAY:
            return 'Earning Day'
        elif val == ScreenerType.UNUSUAL_VOLUME:
            return 'Unusual Volume'
        elif val == ScreenerType.CHANNEL_UP:
            return 'Channel Up'
        elif val == ScreenerType.DOUBLE_BOTTOM:
            return 'Double Bottom'
        return UNKNOWN

    @staticmethod
    def tochoices():
        return (
            (ScreenerType.MANUAL, ScreenerType.tostr(
                ScreenerType.MANUAL)),
            (ScreenerType.EARNING_DAY, ScreenerType.tostr(
                ScreenerType.EARNING_DAY)),
            (ScreenerType.UNUSUAL_VOLUME, ScreenerType.tostr(
                ScreenerType.UNUSUAL_VOLUME)),
            (ScreenerType.CHANNEL_UP, ScreenerType.tostr(
                ScreenerType.CHANNEL_UP)),
            (ScreenerType.DOUBLE_BOTTOM, ScreenerType.tostr(
                ScreenerType.DOUBLE_BOTTOM)),
        )


class TradingHourType:
    REGULAR = 0
    BEFORE_MARKET_OPEN = 1
    AFTER_MARKET_CLOSE = 2

    @staticmethod
    def tostr(val):
        if val == TradingHourType.REGULAR:
            return 'Regular Hour'
        if val == TradingHourType.BEFORE_MARKET_OPEN:
            return 'Before Market Open'
        elif val == TradingHourType.AFTER_MARKET_CLOSE:
            return "After Market Close"
        return UNKNOWN

    @staticmethod
    def tochoices():
        return (
            (TradingHourType.REGULAR, TradingHourType.tostr(
                TradingHourType.REGULAR)),
            (TradingHourType.BEFORE_MARKET_OPEN, TradingHourType.tostr(
                TradingHourType.BEFORE_MARKET_OPEN)),
            (TradingHourType.AFTER_MARKET_CLOSE, TradingHourType.tostr(
                TradingHourType.AFTER_MARKET_CLOSE)),
        )

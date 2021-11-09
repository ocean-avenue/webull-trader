# trading config

# min gap ratio for momo, breakout strategy
MIN_SURGE_CHANGE_RATIO = 0.04
# min surge volume for momo, breakout strategy
MIN_SURGE_VOLUME = 6000.0
# surge amount = surge volume x price
MIN_SURGE_AMOUNT = 15000.0
# average confirm volume in regular market
AVG_CONFIRM_VOLUME = 1000000.0
PAPER_AVG_CONFIRM_VOLUME = 30000.0
# average confirm volume in extended market
EXTENDED_AVG_CONFIRM_VOLUME = 50000.0
PAPER_EXTENDED_AVG_CONFIRM_VOLUME = 3000.0
# average confirm amount in regular market
AVG_CONFIRM_AMOUNT = 120000.0
# average confirm amount in extended market
EXTENDED_AVG_CONFIRM_AMOUNT = 12000.0
# trading observe timeout in seconds
OBSERVE_TIMEOUT_IN_SEC = 300
# buy after sell interval in seconds
TRADE_INTERVAL_IN_SEC = 90
# pending order timeout in seconds
PENDING_ORDER_TIMEOUT_IN_SEC = 60
# holding order timeout in seconds
HOLDING_ORDER_TIMEOUT_IN_SEC = 1800
# level 2, (ask - bid) / bid
MAX_BID_ASK_GAP_RATIO = 0.02
# refresh login interval minutes
REFRESH_LOGIN_INTERVAL_IN_MIN = 10
# trading blacklist timeout in seconds
BLACKLIST_TIMEOUT_IN_SEC = 1800
# max previous day close gap ratio for red/green strategy
MAX_PREV_DAY_CLOSE_GAP_RATIO = 0.02
# relative volume required for day trade entry
DAY_MIN_RELATIVE_VOLUME = 1.5
DAY_EXTENDED_MIN_RELATIVE_VOLUME = 2.0
# relative volume required for swint trade entry
SWING_MIN_RELATIVE_VOLUME = 2.0
# earning gap ratio for earning strategy
MIN_EARNING_GAP_RATIO = 0.05
# period high price gap ratio
PERIOD_HIGH_PRICE_GAP_RATIO = 1.01
# long wick avg candle body ratio
LONG_WICK_AVG_CANDLE_RATIO = 1.1
# long wick pre candle body ratio
LONG_WICK_PREV_CANDLE_RATIO = 0.9
# long wick change ratio
LONG_WICK_CHANGE_RATIO = 0.05
# long wick up candle ratio
LONG_WICK_UP_RATIO = 2.5
# ROC for day trade entry
DAY_PRICE_RATE_OF_CHANGE = 5
# ROC for day trade scale in
DAY_SCALE_PRICE_RATE_OF_CHANGE = 2
# ROC for swing trade entry
SWING_PRICE_RATE_OF_CHANGE = 30
# ROC for swing trade scale in
SWING_SCALE_PRICE_RATE_OF_CHANGE = 12
# incrase ratio of bid price for buy
BUY_BID_PRICE_RATIO = 1.01
# day trading min stop loss 2%
MIN_DAY_STOP_LOSS = 0.02
# day trading max stop loss 5%
MAX_DAY_STOP_LOSS = 0.05
# trading period timeout in seconds
DAY_PERIOD_TIMEOUT_IN_SEC = 90
# iterations for clear position
CLEAR_POSITION_ITERATIONS = 80
# target units for day trade
DAY_TARGET_UNITS = 12
# target units for day trade in extended hour
DAY_EXTENDED_TARGET_UNITS = 4
# threshold for check is chart most green candles
CHART_MOST_GREEN_CANDLES_THRESHOLD = 0.8
CHART_MORE_GREEN_CANDLES_THRESHOLD = 0.6
# bearish avg candle body ratio
BEARISH_AVG_CANDLE_RATIO = 1.4
# max current candle surge ratio for day trade entry
MAX_DAY_ENTRY_CANDLE_SURGE_RATIO = 0.2
# candle check count for day trade buy the dip scale in
DAY_BUY_DIP_CANDLE_CHECK_COUNT = 5
# volume to my position size ratio
DAY_VOLUME_POS_SIZE_RATIO = 10
DAY_EXTENDED_VOLUME_POS_SIZE_RATIO = 5

# memcache config

CACHE_TIMEOUT = 60 * 10


# twilio config
TWLO_SENDER_NUMBER = "+19789484010"
TWLO_MESSAGE_MAX_LENGTH = 1000


# color config

PROFIT_COLOR = "#4bbf73"
LOSS_COLOR = "#d9534f"

BUY_COLOR = "#0b5345"
SELL_COLOR = "#78281f"

# trading config

# min gap ratio for momo, breakout strategy
MIN_SURGE_CHANGE_RATIO = 0.04
# min surge volume for momo, breakout strategy
MIN_SURGE_VOLUME = 6000.0
# surge amount = surge volume x price
MIN_SURGE_AMOUNT = 15000.0
# average confirm volume in regular market
AVG_CONFIRM_VOLUME = 300000.0
# average confirm volume in extended market
EXTENDED_AVG_CONFIRM_VOLUME = 3000.0
# average confirm amount in regular market
AVG_CONFIRM_AMOUNT = 3000000.0
# average confirm amount in extended market
EXTENDED_AVG_CONFIRM_AMOUNT = 30000.0
# trading observe timeout in seconds
OBSERVE_TIMEOUT_IN_SEC = 300
# buy after sell interval in seconds
TRADE_INTERVAL_IN_SEC = 60
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
# relative volume required for entry
MIN_RELATIVE_VOLUME = 3.0
# earning gap ratio for earning strategy
MIN_EARNING_GAP_RATIO = 0.05
# long wick up candle ratio
LONG_WICK_UP_RATIO = 2.5

# color config

PROFIT_COLOR = "#4bbf73"
LOSS_COLOR = "#d9534f"

BUY_COLOR = "#0b5345"
SELL_COLOR = "#78281f"

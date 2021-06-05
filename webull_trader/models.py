from django.db import models
from webull_trader import enums

# Create your models here.


class TradingSettings(models.Model):
    paper = models.BooleanField(default=True)
    algo_type = models.PositiveSmallIntegerField(
        choices=enums.AlgorithmType.tochoices(),
        default=enums.AlgorithmType.DAY_MOMENTUM
    )
    # position amount for day trade
    order_amount_limit = models.FloatField()
    # surge amount = surge volume x price
    min_surge_amount = models.FloatField()
    # min surge volume for momo strategy
    min_surge_volume = models.FloatField()
    # min gap ratio for momo strategy
    min_surge_change_ratio = models.FloatField()
    # average confirm volume in regular market
    avg_confirm_volume = models.FloatField()
    # trading observe timeout in seconds
    observe_timeout_in_sec = models.IntegerField()
    # buy after sell interval in seconds
    trade_interval_in_sec = models.IntegerField()
    # pending order timeout in seconds
    pending_order_timeout_in_sec = models.IntegerField()
    # holding order timeout in seconds
    holding_order_timeout_in_sec = models.IntegerField()
    # level 2, (ask - bid) / bid
    max_bid_ask_gap_ratio = models.FloatField()
    target_profit_ratio = models.FloatField()
    # stop loss ratio
    stop_loss_ratio = models.FloatField()
    # refresh login interval minutes
    refresh_login_interval_in_min = models.IntegerField()
    # trading blacklist timeout in seconds
    blacklist_timeout_in_sec = models.IntegerField()
    # swing buy order limit
    swing_position_amount_limit = models.FloatField()
    # max previous day close gap ratio for red/green strategy
    max_prev_day_close_gap_ratio = models.FloatField()
    # relative volume required for entry
    min_relative_volume = models.FloatField()
    # earning gap ratio for earning strategy
    min_earning_gap_ratio = models.FloatField()
    # usable cash for day trade use
    day_trade_usable_cash_threshold = models.FloatField()

    def __str__(self):
        return "Trading settings, paper: {}, order amount limit: {}, algo: {}".format(
            self.paper, self.order_amount_limit, enums.AlgorithmType.tostr(self.algo_type))


class TradingLog(models.Model):
    date = models.DateField()
    tag = models.CharField(max_length=128)
    trading_hour = models.PositiveSmallIntegerField(
        choices=enums.TradingHourType.tochoices(),
        default=enums.TradingHourType.REGULAR
    )
    log_text = models.TextField(null=True, blank=True)

    def __str__(self):
        return "[{}] {}: {}".format(self.date, self.tag, self.log_text)


class WebullCredentials(models.Model):
    cred = models.TextField(null=True, blank=True)
    paper = models.BooleanField(default=True)

    def __str__(self):
        account_type = "LIVE"
        if self.paper:
            account_type = "PAPER"
        return "Credentials for {} webull account".format(account_type)


class WebullOrder(models.Model):
    order_id = models.CharField(max_length=128)
    ticker_id = models.CharField(max_length=128)
    symbol = models.CharField(max_length=64)
    ACTION_TYPE_CHOICES = (
        (enums.ActionType.BUY, enums.ActionType.tostr(enums.ActionType.BUY)),
        (enums.ActionType.SELL, enums.ActionType.tostr(enums.ActionType.SELL)),
    )
    action = models.PositiveSmallIntegerField(
        choices=ACTION_TYPE_CHOICES,
        default=enums.ActionType.BUY
    )
    status = models.CharField(max_length=64)
    total_quantity = models.PositiveIntegerField(default=1)
    filled_quantity = models.PositiveIntegerField(default=1)
    price = models.FloatField()
    avg_price = models.FloatField()
    order_type = models.PositiveSmallIntegerField(
        choices=enums.OrderType.tochoices(),
        default=enums.OrderType.LMT
    )

    filled_time = models.DateTimeField(
        auto_now_add=False, auto_now=False, null=True, blank=True)
    placed_time = models.DateTimeField(
        auto_now_add=False, auto_now=False, null=True, blank=True)
    time_in_force = models.PositiveSmallIntegerField(
        choices=enums.TimeInForceType.tochoices(),
        default=enums.TimeInForceType.GTC
    )
    paper = models.BooleanField(default=True)

    setup = models.PositiveSmallIntegerField(
        choices=enums.SetupType.tochoices(),
        default=enums.SetupType.UNKNOWN
    )

    def __str__(self):
        return "[{}] <{}> {} total: {}, filled: {}, price: ${}, avg: ${}".format(
            self.placed_time,
            self.symbol,
            enums.ActionType.tostr(self.action),
            self.total_quantity,
            self.filled_quantity,
            self.price,
            self.avg_price)


class WebullOrderNote(models.Model):
    order_id = models.CharField(max_length=128)
    setup = models.PositiveSmallIntegerField(
        choices=enums.SetupType.tochoices(),
        default=enums.SetupType.DAY_FIRST_CANDLE_NEW_HIGH
    )
    note = models.TextField(null=True, blank=True)

    def __str__(self):
        setup_str = enums.SetupType.tostr(self.setup)
        return "{}: {}, {}".format(self.order_id, setup_str, self.note)


class WebullNews(models.Model):
    news_id = models.CharField(max_length=128)
    symbol = models.CharField(max_length=64)
    title = models.CharField(max_length=512)
    source_name = models.CharField(max_length=64)
    collect_source = models.CharField(max_length=64)
    news_time = models.CharField(max_length=64)
    summary = models.TextField()
    news_url = models.URLField(max_length=200)

    date = models.DateField(auto_now=False, auto_now_add=False)

    def __str__(self):
        return "[{}] <{}>: {}".format(self.date, self.symbol, self.title)


class WebullAccountStatistics(models.Model):
    net_liquidation = models.FloatField()
    total_profit_loss = models.FloatField()
    total_profit_loss_rate = models.FloatField()
    day_profit_loss = models.FloatField()

    date = models.DateField(auto_now=False, auto_now_add=False)

    def __str__(self):
        return "[{}] day P&L: {}".format(self.date, self.day_profit_loss)


class EarningCalendar(models.Model):
    symbol = models.CharField(max_length=64)
    earning_date = models.DateField()
    earning_time = models.CharField(max_length=32)
    eps = models.FloatField(null=True, blank=True, default=None)
    eps_estimated = models.FloatField(null=True, blank=True, default=None)
    revenue = models.FloatField(default=0)
    revenue_estimated = models.FloatField(default=0)

    price = models.FloatField()
    change = models.FloatField()
    change_percentage = models.FloatField()
    year_high = models.FloatField()
    year_low = models.FloatField()
    market_value = models.FloatField()
    avg_price_50d = models.FloatField()
    avg_price_200d = models.FloatField()
    volume = models.FloatField()
    avg_volume = models.FloatField()
    exchange = models.CharField(max_length=64)
    outstanding_shares = models.FloatField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "[{}] <{}> ({})".format(self.earning_date, self.symbol, self.earning_time)


class HistoricalTopGainer(models.Model):
    symbol = models.CharField(max_length=64)
    ticker_id = models.CharField(max_length=128)
    change = models.FloatField()
    change_percentage = models.FloatField()
    price = models.FloatField()

    date = models.DateField(auto_now=False, auto_now_add=False)

    def __str__(self):
        return "[{}] <{}> top gainer: +{}%".format(self.date, self.symbol, round(self.change_percentage * 100, 2))


class HistoricalTopLoser(models.Model):
    symbol = models.CharField(max_length=64)
    ticker_id = models.CharField(max_length=128)
    change = models.FloatField()
    change_percentage = models.FloatField()
    price = models.FloatField()

    date = models.DateField(auto_now=False, auto_now_add=False)

    def __str__(self):
        return "[{}] <{}> top loser: {}%".format(self.date, self.symbol, round(self.change_percentage * 100, 2))


class HistoricalKeyStatistics(models.Model):
    symbol = models.CharField(max_length=64)
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    change = models.FloatField()
    change_ratio = models.FloatField()
    market_value = models.FloatField()
    volume = models.FloatField()
    turnover_rate = models.FloatField(null=True, blank=True)
    # range %
    vibrate_ratio = models.FloatField(null=True, blank=True)
    avg_vol_10d = models.FloatField()
    avg_vol_3m = models.FloatField()
    pe = models.FloatField(null=True, blank=True)
    forward_pe = models.FloatField(null=True, blank=True)
    pe_ttm = models.FloatField(null=True, blank=True)
    eps = models.FloatField(null=True, blank=True)
    eps_ttm = models.FloatField(null=True, blank=True)
    pb = models.FloatField(null=True, blank=True)
    ps = models.FloatField(null=True, blank=True)
    bps = models.FloatField(null=True, blank=True)
    short_float = models.FloatField(null=True, blank=True)
    # shares outstand
    total_shares = models.FloatField(null=True, blank=True)
    # free float
    outstanding_shares = models.FloatField(null=True, blank=True)
    fifty_two_wk_high = models.FloatField()
    fifty_two_wk_low = models.FloatField()
    latest_earnings_date = models.CharField(max_length=128)
    estimate_earnings_date = models.CharField(max_length=128)

    date = models.DateField(auto_now=False, auto_now_add=False)

    def __str__(self):
        return "[{}] <{}> historical mktcap: {}".format(self.date, self.symbol, self.market_value)


class HistoricalMinuteBar(models.Model):
    symbol = models.CharField(max_length=64)
    date = models.DateField(auto_now=False, auto_now_add=False)
    time = models.DateTimeField(auto_now=False, auto_now_add=False)
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    volume = models.FloatField()
    vwap = models.FloatField()

    def __str__(self):
        return "[{}] <{}> O:{}, H:{}, L:{}, C:{}".format(self.time, self.symbol, self.open, self.high, self.low, self.close)


class HistoricalDailyBar(models.Model):
    symbol = models.CharField(max_length=64)
    date = models.DateField(auto_now=False, auto_now_add=False)
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    volume = models.FloatField()

    def __str__(self):
        return "[{}] <{}> O:{}, H:{}, L:{}, C:{}".format(self.date, self.symbol, self.open, self.high, self.low, self.close)


class HistoricalDayTradePerformance(models.Model):
    date = models.DateField(auto_now=False, auto_now_add=False)
    win_rate = models.FloatField()
    profit_loss_ratio = models.FloatField()
    day_profit_loss = models.FloatField()
    trades = models.PositiveIntegerField()

    top_gain_amount = models.FloatField()
    top_gain_symbol = models.CharField(max_length=64)
    top_loss_amount = models.FloatField()
    top_loss_symbol = models.CharField(max_length=64)

    def __str__(self):
        return "[{}] P&L: {}, {} trades".format(self.date, self.day_profit_loss, self.trades)


class SwingWatchlist(models.Model):
    symbol = models.CharField(max_length=64)
    screener_type = models.PositiveSmallIntegerField(
        choices=enums.ScreenerType.tochoices(),
        default=enums.ScreenerType.MANUAL
    )
    units = models.PositiveSmallIntegerField(default=1)
    sector = models.CharField(max_length=64, default="Technology")
    exchange = models.CharField(max_length=64, default="NASDAQ")
    is_etf = models.BooleanField(default=False)

    created_date = models.DateField(auto_now_add=True)
    updated_date = models.DateField(auto_now=True)

    def __str__(self):
        return "[{}] <{}> ({})".format(self.updated_date, self.symbol, enums.ScreenerType.tostr(self.screener_type))


class SwingPosition(models.Model):
    order_id = models.CharField(max_length=128)
    symbol = models.CharField(max_length=64)
    cost = models.FloatField()
    quantity = models.PositiveIntegerField(default=0)
    buy_date = models.DateField()
    buy_time = models.DateTimeField()

    setup = models.PositiveSmallIntegerField(
        choices=enums.SetupType.tochoices(),
        default=enums.SetupType.SWING_20_DAYS_NEW_HIGH
    )

    def __str__(self):
        return "[{}] <{}> x{} ${}".format(self.buy_date, self.symbol, self.quantity, self.cost)


class SwingTrade(models.Model):
    symbol = models.CharField(max_length=64)
    quantity = models.PositiveIntegerField()

    buy_date = models.DateField()
    buy_time = models.DateTimeField()
    buy_price = models.FloatField()
    buy_order_id = models.CharField(max_length=128)

    sell_date = models.DateField()
    sell_time = models.DateTimeField()
    sell_price = models.FloatField()
    sell_order_id = models.CharField(max_length=128)

    setup = models.PositiveSmallIntegerField(
        choices=enums.SetupType.tochoices(),
        default=enums.SetupType.SWING_20_DAYS_NEW_HIGH
    )
    note = models.TextField(null=True, blank=True)

    def __str__(self):
        return "[{}] <{}> x{} ${}/${}".format(self.sell_date, self.symbol, self.quantity, self.buy_price, self.sell_price)


class SwingHistoricalDailyBar(models.Model):
    symbol = models.CharField(max_length=64)
    date = models.DateField(auto_now=False, auto_now_add=False)
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    volume = models.FloatField()

    rsi_10 = models.FloatField()
    sma_55 = models.FloatField()
    sma_120 = models.FloatField()

    def __str__(self):
        return "[{}] <{}> O:{}, H:{}, L:{}, C:{}".format(self.date, self.symbol, self.open, self.high, self.low, self.close)


class OvernightPosition(models.Model):
    order_id = models.CharField(max_length=128)
    symbol = models.CharField(max_length=64)
    ticker_id = models.CharField(max_length=128)
    cost = models.FloatField()
    quantity = models.PositiveIntegerField(default=0)
    buy_date = models.DateField()
    buy_time = models.DateTimeField()

    setup = models.PositiveSmallIntegerField(
        choices=enums.SetupType.tochoices(),
        default=enums.SetupType.DAY_EARNINGS_GAP
    )

    def __str__(self):
        return "[{}] <{}> x{} ${}".format(self.buy_date, self.symbol, self.quantity, self.cost)


class OvernightTrade(models.Model):
    symbol = models.CharField(max_length=64)
    quantity = models.PositiveIntegerField()

    buy_date = models.DateField()
    buy_time = models.DateTimeField()
    buy_price = models.FloatField()
    buy_order_id = models.CharField(max_length=128)

    sell_date = models.DateField()
    sell_time = models.DateTimeField()
    sell_price = models.FloatField()
    sell_order_id = models.CharField(max_length=128)

    setup = models.PositiveSmallIntegerField(
        choices=enums.SetupType.tochoices(),
        default=enums.SetupType.DAY_EARNINGS_GAP
    )
    note = models.TextField(null=True, blank=True)

    def __str__(self):
        return "[{}] <{}> x{} ${}/${}".format(self.sell_date, self.symbol, self.quantity, self.buy_price, self.sell_price)

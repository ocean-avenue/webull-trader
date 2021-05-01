from django.db import models
from old_ross import enums

# Create your models here.


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

    filled_time = models.DateTimeField(auto_now_add=False, auto_now=False)
    placed_time = models.DateTimeField(auto_now_add=False, auto_now=False)
    TIME_IN_FORCE_TYPE_CHOICES = (
        (enums.TimeInForceType.GTC, enums.TimeInForceType.tostr(
            enums.TimeInForceType.GTC)),
        (enums.TimeInForceType.DAY, enums.TimeInForceType.tostr(
            enums.TimeInForceType.DAY)),
        (enums.TimeInForceType.IOC, enums.TimeInForceType.tostr(
            enums.TimeInForceType.IOC)),
    )
    time_in_force = models.PositiveSmallIntegerField(
        choices=TIME_IN_FORCE_TYPE_CHOICES,
        default=enums.TimeInForceType.GTC
    )
    paper = models.BooleanField(default=True)

    def __str__(self):
        return "[{}] <{}> {} total: {}, filled: {}, price: ${}, avg: ${}".format(
            self.filled_time,
            enums.ActionType.tostr(self.action),
            self.stock.symbol,
            self.total_quantity,
            self.filled_quantity,
            self.price,
            self.avg_price)


class WebullOrderNote(models.Model):
    order_id = models.CharField(max_length=128)
    note = models.TextField(null=True, blank=True)

    def __str__(self):
        return "{}: {}".format(self.order_id, self.note)


class WebullNews(models.Model):
    news_id = models.CharField(max_length=128)
    symbol = models.CharField(max_length=64)
    title = models.CharField(max_length=512)
    source = models.CharField(max_length=64)
    news_time = models.CharField(max_length=64)
    summary = models.TextField()
    news_url = models.URLField(max_length=200)
    trade_date = models.DateField(auto_now=False, auto_now_add=False)

    def __str__(self):
        return "[{}] <{}>: {}".format(self.trade_date, self.symbol, self.title)


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
    turnover_rate = models.FloatField()
    vibrate_ratio = models.FloatField()
    avg_vol_10d = models.FloatField()
    avg_vol_3m = models.FloatField()
    pe = models.FloatField()
    forward_pe = models.FloatField()
    pe_ttm = models.FloatField()
    eps = models.FloatField()
    eps_ttm = models.FloatField()
    pb = models.FloatField()
    ps = models.FloatField()
    bps = models.FloatField()
    total_shares = models.FloatField()
    outstanding_shares = models.FloatField()
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
        return "[{}] <{}> O:{}, H:{}, L:{}, C:{}".format(self.time, self.symbol, self.open, self.high, self.low, self.close)

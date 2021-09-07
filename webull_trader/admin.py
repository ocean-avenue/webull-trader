from django.contrib import admin
from django.utils.html import format_html
from webull_trader import models

# Register your models here.


class TradingSettingsAdmin(admin.ModelAdmin):
    list_display = [
        'paper',
        'algo_type',
        'order_amount_limit',
        'day_free_float_limit_in_million',
        'day_sectors_limit',
        'day_trade_usable_cash_threshold',
        'swing_position_amount_limit',
    ]


admin.site.register(models.TradingSettings, TradingSettingsAdmin)


class TradingLogAdmin(admin.ModelAdmin):
    list_display = [
        'date',
        'tag',
        'trading_hour',
        # 'log_text',
    ]


admin.site.register(models.TradingLog, TradingLogAdmin)


class ExceptionLogAdmin(admin.ModelAdmin):
    list_display = [
        'exception',
        'created_at',
    ]


admin.site.register(models.ExceptionLog, ExceptionLogAdmin)


class TradingSymbolsAdmin(admin.ModelAdmin):
    list_display = [
        'symbols',
        'updated_at',
    ]


admin.site.register(models.TradingSymbols, TradingSymbolsAdmin)


class WebullCredentialsAdmin(admin.ModelAdmin):

    list_display = [
        'paper',
        'cred',
        'trade_pwd',
    ]


admin.site.register(models.WebullCredentials, WebullCredentialsAdmin)


class WebullOrderAdmin(admin.ModelAdmin):

    list_display = [
        'symbol',
        'order_id',
        'ticker_id',
        'setup',
        'action',
        'status',
        'total_quantity',
        'filled_quantity',
        'price',
        'avg_price',
        'order_type',
        'filled_time',
        'placed_time',
        'time_in_force',
        'paper',
    ]


admin.site.register(models.WebullOrder, WebullOrderAdmin)


class WebullOrderNoteAdmin(admin.ModelAdmin):

    list_display = [
        'order_id',
        'setup',
        'note',
    ]


admin.site.register(models.WebullOrderNote, WebullOrderNoteAdmin)


class WebullNewsAdmin(admin.ModelAdmin):

    def news_link(self, obj):
        return format_html('<a href="{}" target="_blank">{}</a>'.format(obj.news_url, obj.news_url))

    list_display = [
        'symbol',
        'news_id',
        'date',
        'title',
        'source_name',
        'collect_source',
        'news_time',
        'summary',
        'news_link',
    ]


admin.site.register(models.WebullNews, WebullNewsAdmin)


class WebullAccountStatisticsAdmin(admin.ModelAdmin):

    list_display = [
        'date',
        'net_liquidation',
        'total_profit_loss',
        'total_profit_loss_rate',
        'day_profit_loss',
    ]


admin.site.register(models.WebullAccountStatistics,
                    WebullAccountStatisticsAdmin)


class StockQuoteAdmin(admin.ModelAdmin):

    list_display = [
        'symbol',
        'price',
        'beta',
        'market_value',
        'price_range',
        'sector',
    ]


admin.site.register(models.StockQuote,
                    StockQuoteAdmin)


class EarningCalendarAdmin(admin.ModelAdmin):

    list_display = [
        'symbol',
        'earning_date',
        'earning_time',
        'eps',
        'eps_estimated',
        'revenue',
        'revenue_estimated'
    ]


admin.site.register(models.EarningCalendar,
                    EarningCalendarAdmin)


# class HistoricalTopGainerAdmin(admin.ModelAdmin):

#     list_display = [
#         'symbol',
#         'date',
#         'change',
#         'change_percentage',
#         'price',
#     ]


# admin.site.register(models.HistoricalTopGainer,
#                     HistoricalTopGainerAdmin)


# class HistoricalTopLoserAdmin(admin.ModelAdmin):

#     list_display = [
#         'symbol',
#         'date',
#         'change',
#         'change_percentage',
#         'price',
#     ]


# admin.site.register(models.HistoricalTopLoser,
#                     HistoricalTopLoserAdmin)


class HistoricalKeyStatisticsAdmin(admin.ModelAdmin):

    list_display = [
        'symbol',
        'date',
        'open',
        'high',
        'low',
        'close',
        'change',
        'change_ratio',
        'market_value',
        'volume',
        'turnover_rate',
        'vibrate_ratio',
        'avg_vol_10d',
        'avg_vol_3m',
        'pe',
        'forward_pe',
        'pe_ttm',
        'eps',
        'eps_ttm',
        'pb',
        'ps',
        'bps',
        'total_shares',
        'outstanding_shares',
        'fifty_two_wk_high',
        'fifty_two_wk_low',
        'latest_earnings_date',
        'estimate_earnings_date',
        'short_float',
    ]


admin.site.register(models.HistoricalKeyStatistics,
                    HistoricalKeyStatisticsAdmin)


class HistoricalMinuteBarAdmin(admin.ModelAdmin):

    list_display = [
        'symbol',
        'time',
        'open',
        'high',
        'low',
        'close',
        'volume',
        'vwap',
    ]


admin.site.register(models.HistoricalMinuteBar, HistoricalMinuteBarAdmin)


class HistoricalDailyBarAdmin(admin.ModelAdmin):

    list_display = [
        'symbol',
        'date',
        'open',
        'high',
        'low',
        'close',
        'volume',
    ]


admin.site.register(models.HistoricalDailyBar, HistoricalDailyBarAdmin)


class DayPositionAdmin(admin.ModelAdmin):
    list_display = [
        'symbol',
        'total_cost',
        'quantity',
        'setup',
        'add_unit_price',
        'stop_loss_price',
        'buy_date',
        'buy_time',
        'require_adjustment',
        'order_ids',
    ]


admin.site.register(models.DayPosition,
                    DayPositionAdmin)


class DayTradeAdmin(admin.ModelAdmin):
    list_display = [
        'symbol',
        'total_cost',
        'total_sold',
        'quantity',
        'buy_date',
        'sell_date',
        'setup',
        'require_adjustment',
        'order_ids',
    ]


admin.site.register(models.DayTrade,
                    DayTradeAdmin)


class HistoricalDayTradePerformanceAdmin(admin.ModelAdmin):
    list_display = [
        'date',
        'day_profit_loss',
        'trades',
        'win_rate',
        'profit_loss_ratio',
        'top_gain_amount',
        'top_gain_symbol',
        'top_loss_amount',
        'top_loss_symbol',
        'total_buy_amount',
        'total_sell_amount',
    ]


admin.site.register(models.HistoricalDayTradePerformance,
                    HistoricalDayTradePerformanceAdmin)


class HistoricalSwingTradePerformanceAdmin(admin.ModelAdmin):
    list_display = [
        'date',
        'day_profit_loss',
        'trades',
        'total_buy_amount',
        'total_sell_amount',
    ]


admin.site.register(models.HistoricalSwingTradePerformance,
                    HistoricalSwingTradePerformanceAdmin)


class SwingWatchlistAdmin(admin.ModelAdmin):
    list_display = [
        'symbol',
        'screener_type',
        'sector',
        'unit_weight',
        'is_etf',
        'updated_date',
        'created_date',
    ]


admin.site.register(models.SwingWatchlist,
                    SwingWatchlistAdmin)


class SwingPositionAdmin(admin.ModelAdmin):
    list_display = [
        'symbol',
        'total_cost',
        'quantity',
        'setup',
        'add_unit_price',
        'stop_loss_price',
        'buy_date',
        'buy_time',
        'require_adjustment',
        'order_ids',
    ]


admin.site.register(models.SwingPosition,
                    SwingPositionAdmin)


class SwingTradeAdmin(admin.ModelAdmin):
    list_display = [
        'symbol',
        'total_cost',
        'total_sold',
        'quantity',
        'buy_date',
        'sell_date',
        'setup',
        'require_adjustment',
        'order_ids',
        'note',
    ]


admin.site.register(models.SwingTrade,
                    SwingTradeAdmin)


class SwingHistoricalDailyBarAdmin(admin.ModelAdmin):

    list_display = [
        'symbol',
        'date',
        'open',
        'high',
        'low',
        'close',
        'volume',
    ]


admin.site.register(models.SwingHistoricalDailyBar,
                    SwingHistoricalDailyBarAdmin)


class ManualTradeRequestAdmin(admin.ModelAdmin):
    list_display = [
        'symbol',
        'quantity',
        'action',
        'setup',
        'complete',
        'created_at',
        'updated_at',
    ]


admin.site.register(models.ManualTradeRequest,
                    ManualTradeRequestAdmin)


class NotifiedErrorExecutionAdmin(admin.ModelAdmin):
    list_display = [
        'execution_id',
        'notified_time',
    ]


admin.site.register(models.NotifiedErrorExecution,
                    NotifiedErrorExecutionAdmin)

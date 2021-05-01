from django.contrib import admin
from old_ross import models

# Register your models here.


class WebullCredentialsAdmin(admin.ModelAdmin):

    list_display = [
        'cred',
        'paper',
    ]


admin.site.register(models.WebullCredentials, WebullCredentialsAdmin)


class WebullOrderAdmin(admin.ModelAdmin):

    list_display = [
        'order_id',
        'ticker_id',
        'symbol',
        'action',
        'status',
        'total_quantity',
        'filled_quantity',
        'price',
        'avg_price',
        'filled_time',
        'placed_time',
        'time_in_force',
        'paper',
    ]


admin.site.register(models.WebullOrder, WebullOrderAdmin)


class WebullOrderNoteAdmin(admin.ModelAdmin):

    list_display = [
        'order_id',
        'note',
    ]


admin.site.register(models.WebullOrderNote, WebullOrderNoteAdmin)


class WebullNewsAdmin(admin.ModelAdmin):

    list_display = [
        'news_id',
        'symbol',
        'title',
        'source',
        'news_time',
        'summary',
        'news_url',
        'trade_date',
    ]


admin.site.register(models.WebullNews, WebullNewsAdmin)


class HistoricalKeyStatisticsAdmin(admin.ModelAdmin):

    list_display = [
        'symbol',
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
        'date',
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

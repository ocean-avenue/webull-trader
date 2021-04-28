from django.contrib import admin
from old_ross import models

# Register your models here.


class WebullOrderAdmin(admin.ModelAdmin):

    list_display = [
        'id',
        'order_id',
        'symbol',
        'side',
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
        'id',
        'order_id',
        'note',
    ]


admin.site.register(models.WebullOrderNote, WebullOrderNoteAdmin)


class WebullNewsAdmin(admin.ModelAdmin):

    list_display = [
        'id',
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

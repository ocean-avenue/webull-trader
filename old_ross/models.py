from django.db import models
from old_ross import enums

# Create your models here.


class WebullOrder(models.Model):
    symbol = models.CharField(max_length=64)
    SIDE_TYPE_CHOICES = (
        (enums.SideType.BUY, enums.SideType.tostr(enums.SideType.BUY)),
        (enums.SideType.SELL, enums.SideType.tostr(enums.SideType.SELL)),
    )
    side = models.PositiveSmallIntegerField(
        choices=SIDE_TYPE_CHOICES,
        default=enums.SideType.BUY
    )
    status = models.CharField(max_length=64)
    total_quantity = models.PositiveIntegerField(default=1)
    filled_quantity = models.PositiveIntegerField(default=1)
    price = models.FloatField()
    avg_price = models.FloatField()

    filled_time = models.DateTimeField(auto_now_add=False, auto_now=False)
    placed_time = models.DateTimeField(auto_now_add=False, auto_now=False)
    TIME_IN_FORCE_TYPE_CHOICES = (
        (enums.TimeInForceType.GTC, enums.TimeInForceType.tostr(enums.TimeInForceType.GTC)),
        (enums.TimeInForceType.DAY, enums.TimeInForceType.tostr(enums.TimeInForceType.DAY)),
        (enums.TimeInForceType.IOC, enums.TimeInForceType.tostr(enums.TimeInForceType.IOC)),
    )
    time_in_force = models.PositiveSmallIntegerField(
        choices=TIME_IN_FORCE_TYPE_CHOICES,
        default=enums.TimeInForceType.GTC
    )
    paper = models.BooleanField(default=True)
    note = models.CharField(max_length=512)

    def __str__(self):
        return "[{}] <{}> {} total: {}, filled: {}, price: ${}, avg: ${}".format(
            self.filled_time,
            enums.SideType.tostr(self.side),
            self.stock.symbol,
            self.total_quantity,
            self.filled_quantity,
            self.price,
            self.avg_price)

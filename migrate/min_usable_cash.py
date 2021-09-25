# -*- coding: utf-8 -*-

# fill webull account statistics with min usable cash


def start():
    from webull_trader.models import WebullAccountStatistics
    from scripts import utils

    acc_stats = WebullAccountStatistics.objects.all()

    for acc_stat in acc_stats:
        acc_stat.min_usable_cash = 0.0
        acc_stat.save()

    print("[{}] Migrate {} webull account statistics min usable cash done".format(
        utils.get_now(), len(acc_stats)))


if __name__ == "django.core.management.commands.shell":
    start()

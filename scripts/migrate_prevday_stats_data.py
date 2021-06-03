# -*- coding: utf-8 -*-

# recalculate yesterday hist stats data


def start():
    from datetime import date, timedelta
    from scripts import fetch_account, fetch_orders, fetch_news, fetch_earnings, \
        fetch_histdata, calculate_histdata, utils

    # print("[{}] Start fetch account job...".format(utils.get_now()))
    # fetch_account.start()
    # print("[{}] Done fetch account job!".format(utils.get_now()))

    # print("[{}] Start fetch orders job...".format(utils.get_now()))
    # fetch_orders.start()
    # print("[{}] Done fetch orders job!".format(utils.get_now()))

    # print("[{}] Start fetch news job...".format(utils.get_now()))
    # fetch_news.start()
    # print("[{}] Done fetch news job!".format(utils.get_now()))

    # print("[{}] Start fetch earnings job...".format(utils.get_now()))
    # fetch_earnings.start()
    # print("[{}] Done fetch earnings job!".format(utils.get_now()))

    today = date.today()
    yesterday = today - timedelta(days=1)

    print("[{}] Start fetch hist data job...".format(utils.get_now()))
    fetch_histdata.start(day=yesterday)
    print("[{}] Done fetch hist data job!".format(utils.get_now()))

    print("[{}] Start calculate hist data job...".format(utils.get_now()))
    calculate_histdata.start(day=yesterday)
    print("[{}] Done calculate hist data job!".format(utils.get_now()))

    print("[{}] Recalculate yesterday stats data done".format(utils.get_now()))


if __name__ == "django.core.management.commands.shell":
    start()

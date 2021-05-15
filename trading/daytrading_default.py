# -*- coding: utf-8 -*-

# Day Trading
# Default - Trade as much as possible, mainly for collect data.


from scripts import utils
from trading.daytrading_base import DayTradingBase


class DayTradingDefault(DayTradingBase):

    def call_before(self):
        print("[{}] Default - Trade as much as possible, mainly for collect data.".format(utils.get_now()))


def start():
    from scripts import utils
    from trading.daytrading_default import DayTradingDefault

    paper = utils.check_paper()
    daytrading = DayTradingDefault(paper=paper)
    daytrading.start()


if __name__ == "django.core.management.commands.shell":
    start()

# -*- coding: utf-8 -*-

# fetch earning calendar from financialmodelingprep.com into database


def start():
    from sdk import fmpsdk
    from common import utils
    from webull_trader.models import EarningCalendar

    symbol_list = []
    earning_calendars = fmpsdk.get_earning_calendar()
    earning_dist = {}

    for calendar in earning_calendars:
        symbol = calendar["symbol"]
        if '.' in symbol:
            symbol_parts = symbol.split('.')
            symbol = "{}-{}".format(symbol_parts[0], symbol_parts[1])
        # append symbol list
        symbol_list.append(symbol)
        # fill dist
        earning_dist[symbol] = {
            "symbol": symbol,
            "earning_date": calendar["date"],
            "eps": calendar["eps"] or 0,
            "eps_estimated": calendar["epsEstimated"] or 0,
            "earning_time": calendar["time"],
            "revenue": calendar["revenue"] or 0,
            "revenue_estimated": calendar["revenueEstimated"] or 0,
        }

    earning_quotes = fmpsdk.batch_quotes(symbol_list)
    print("[{}] Importing earnings for {} symbols...".format(
        utils.get_now(), len(earning_quotes)))
    # only add earning with quote into datebase
    for quote in earning_quotes:
        symbol = quote["symbol"]
        earning_data = earning_dist[symbol]
        earning_date = earning_data["earning_date"]
        earning = EarningCalendar.objects.filter(
            symbol=symbol).filter(earning_date=earning_date).first()

        if earning == None:
            earning = EarningCalendar(
                symbol=symbol,
                earning_date=earning_date,
            )
        # fill earning data
        earning.earning_time = earning_data["earning_time"]
        earning.eps = earning_data["eps"]
        earning.eps_estimated = earning_data["eps_estimated"]
        earning.revenue = earning_data["revenue"]
        earning.revenue_estimated = earning_data["revenue_estimated"]
        earning.price = quote["price"]
        earning.change = quote["change"]
        earning.change_percentage = quote["changesPercentage"]
        earning.year_high = quote["yearHigh"]
        earning.year_low = quote["yearLow"]
        earning.market_value = quote["marketCap"]
        earning.avg_price_50d = quote["priceAvg50"]
        earning.avg_price_200d = quote["priceAvg200"]
        earning.volume = quote["volume"]
        earning.avg_volume = quote["avgVolume"]
        earning.exchange = quote["exchange"] or ""
        earning.outstanding_shares = quote["sharesOutstanding"]
        earning.save()


if __name__ == "django.core.management.commands.shell":
    start()

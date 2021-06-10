# -*- coding: utf-8 -*-

# fetch stock quotes for swing trades

def start():
    from sdk import fmpsdk
    from webull_trader.models import SwingWatchlist, StockQuote

    swing_watchlist = SwingWatchlist.objects.all()
    symbol_list = []
    for swing_watch in swing_watchlist:
        symbol_list.append(swing_watch.symbol)

    quotes = fmpsdk.get_quotes(symbol_list)
    quote_dist = {}
    for quote in quotes:
        quote_dist[quote["symbol"]] = quote
    profiles = fmpsdk.get_profiles(symbol_list)
    profile_dist = {}
    for profile in profiles:
        profile_dist[profile["symbol"]] = profile
    
    # save stock quote
    for symbol in symbol_list:
        quote = quote_dist[symbol]
        stock_quote = StockQuote.objects.filter(symbol=symbol).first()
        if not quote:
            stock_quote = StockQuote(symbol=symbol)
        stock_quote.price = quote["price"]
        stock_quote.volume = quote["volume"]
        stock_quote.change = quote["change"]
        stock_quote.change_percentage = quote["changesPercentage"]
        stock_quote.market_value = quote["marketCap"]
        stock_quote.avg_price_50d = quote["priceAvg50"]
        stock_quote.avg_price_200d = quote["priceAvg200"]
        stock_quote.avg_volume = quote["avgVolume"]
        stock_quote.exchange = quote["exchange"]
        stock_quote.eps = quote["eps"]
        stock_quote.pe = quote["pe"]
        stock_quote.outstanding_shares = quote["sharesOutstanding"]
        if symbol in profile_dist:
            profile = profile_dist[symbol]
            stock_quote.beta = profile["beta"]
            stock_quote.last_div = profile["lastDiv"]
            stock_quote.price_range = profile["range"]
            stock_quote.sector = profile["sector"]
            stock_quote.industry = profile["industry"]
            stock_quote.is_etf = profile["isEtf"]

if __name__ == "django.core.management.commands.shell":
    start()

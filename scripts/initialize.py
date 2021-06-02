# -*- coding: utf-8 -*-

# initialize script


SWING_WATCHLIST_SYMBOLS = [
    "AAPL", "ABNB", "AMZN", "AMD", "ASML", "AAL", "APHA", "ARRY", "ASAN",
    "ARKK", "ARKQ", "ARKW", "ARKG", "ARKF", "ARKX", "AQB",
    "BABA", "BIGC", "BIDU", "BILI", "BAC", "BRK-B", "BA", "BNTX", "BEKE",
    "COIN", "CAN", "CRM", "CAKE", "CHWY", "COST", "CLOV",
    "DBX", "DOCU", "DQ", "DIS", "DAL", "DKNG", "DDOG", "DHI",
    "EBAY", "EH", "ETSY", "ENPH",
    "F", "FB", "FCX", "FUTU", "FSLY", "FVRR", "FCEL", "FI",
    "GOOG", "GME", "GOCO", "GM", "GOTU",
    "HD", "HOME", "HOFV",
    "IWN", "INTC", "IEA",
    "JPM", "JD", "JKS", "JMIA",
    "KO",
    "LYFT", "LI", "LMND", "LUV", "LITB", "LEN",
    "MA", "MSFT", "MP", "MMM", "MCD", "MTCH",
    "NVDA", "NIO", "NET", "NFLX", "NIU", "NEE", "NNDM", "NUE",
    "OPEN",
    "PYPL", "PLTR", "PINS", "PLUG", "PDD", "PSTG", "PAGS", "PTON",
    "QQQ",
    "RBLX", "ROKU", "ROOT", "RDNT",
    "SPY", "SQ", "SHOP", "SNOW", "SE", "SKLZ", "SNAP", "SPOT", "SPCE", "SAVE",
    "SPG", "SPLK", "SNPS", "STXB", "SUMO", "STNE", "STPK",
    "T", "TSLA", "TSM", "TWTR", "TWLO", "TDOC", "TWOU", "TLRY", "TREE", "TMUS",
    "TOL", "TAL", "TME", "TALO",
    "U", "UBER", "UPWK", "UAL", "UMC", "UEC",
    "V",
    "WMT", "WFC", "WTI", "WBA", "WISH",
    "X", "XPEV",
    "YI",
    "ZM", "ZDGE",
]


def start():
    from scripts import utils
    from webull_trader import enums
    from webull_trader.models import TradingSettings, SwingWatchlist

    trading_settings = TradingSettings.objects.first()
    if not trading_settings:
        trading_settings = TradingSettings(
            paper=True,
            algo_type=enums.AlgorithmType.DAY_MOMENTUM,
            order_amount_limit=1000.0,
            min_surge_amount=15000.0,
            min_surge_volume=3000,
            min_surge_change_ratio=0.04,
            avg_confirm_volume=6000,
            observe_timeout_in_sec=300,
            trade_interval_in_sec=120,
            pending_order_timeout_in_sec=60,
            holding_order_timeout_in_sec=1800,
            max_bid_ask_gap_ratio=0.02,
            target_profit_ratio=0.02,
            stop_loss_ratio=-0.01,
            refresh_login_interval_in_min=10,
            blacklist_timeout_in_sec=1800,
            swing_position_amount_limit=2000.0,
            max_prev_day_close_gap_ratio=0.02,
            min_relative_volume=3.0,
            min_earning_gap_ratio=0.05,
        )
        trading_settings.save()

        print("[{}] Trading settings initialized successful".format(utils.get_now()))
    else:
        print("[{}] Trading settings already initialized!".format(utils.get_now()))

    global SWING_WATCHLIST_SYMBOLS

    for symbol in SWING_WATCHLIST_SYMBOLS:
        watchlist = SwingWatchlist.objects.filter(symbol=symbol).first()
        if not watchlist:
            watchlist = SwingWatchlist(symbol=symbol)
        watchlist.save()

    print("[{}] Swing watchlist initialized successful".format(utils.get_now()))


if __name__ == "django.core.management.commands.shell":
    start()

import logging

from datetime import datetime
from alpaca_trade_api.common import URL
from alpaca_trade_api.stream import Stream

log = logging.getLogger(__name__)


APCA_DATA_URL = "https://data.alpaca.markets"
APCA_PAPER_API_BASE_URL = "https://paper-api.alpaca.markets"
APCA_PAPER_API_KEY = "PKXWBBJ7M52WIZUJGVNL"
APCA_PAPER_API_SECRET = "uBIZAHUqflUVx0qwaJ6wsghxpyfORFLSMpdmuSHI"


async def print_trade(t):
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "trade", t)


async def print_quote(q):
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "quote", q)


async def print_trade_update(tu):
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "trade update", tu)


def main():
    logging.basicConfig(level=logging.INFO)
    feed = "iex"  # <- replace to SIP if you have PRO subscription
    stream = Stream(
        APCA_PAPER_API_KEY,
        APCA_PAPER_API_SECRET,
        base_url=URL(APCA_PAPER_API_BASE_URL),
        data_feed=feed,
        raw_data=True,
    )
    stream.subscribe_trade_updates(print_trade_update)
    stream.subscribe_trades(print_trade, "SQ")
    stream.subscribe_quotes(print_quote, "PLUG")

    @stream.on_bar("TSLA")
    async def _(bar):
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "bar", bar)

    stream.run()


if __name__ == "__main__":
    main()

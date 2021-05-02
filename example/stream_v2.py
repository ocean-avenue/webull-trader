import logging

from datetime import datetime
from alpaca_trade_api.common import URL
from alpaca_trade_api.stream import Stream

from credentials.apca import APCA_PAPER_API_KEY, APCA_PAPER_API_SECRET
from sdk.config import APCA_DATA_URL, APCA_PAPER_API_BASE_URL


log = logging.getLogger(__name__)


async def print_trade(t):
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "trade", t)


async def print_quote(q):
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "quote", q)


async def print_bar(b):
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "bar", b)


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
    # stream.subscribe_trade_updates(print_trade_update)
    stream.subscribe_trades(print_trade, "SQ")
    # stream.subscribe_quotes(print_quote, "PLUG")
    # stream.subscribe_bars(print_bar, "TSLA")

    # @stream.on_bar("TSLA")
    # async def _(bar):
    #     print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "bar", bar)

    stream.run()


if __name__ == "__main__":
    main()

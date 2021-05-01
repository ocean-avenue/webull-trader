# https://alpaca.markets/docs/api-documentation/
APCA_DATA_URL = "https://data.alpaca.markets"
APCA_PAPER_API_BASE_URL = "https://paper-api.alpaca.markets"

# https://financialmodelingprep.com/developer/docs
FMP_API_BASE_URL = "https://financialmodelingprep.com/api/v3"

# https://finance.yahoo.com/gainers
YF_GAINERS_URL = "https://finance.yahoo.com/gainers?count=100"

# https://app.webull.com/market/region/6

WEBULL_TICKER_QUOTE_URL = "https://quotes-gw.webullbroker.com/api/quotes/ticker/getTickerRealTime?tickerId={}&includeSecu=1&includeQuote=1"
WEBULL_TOP_GAINERS_URL = "https://quotes-gw.webullfintech.com/api/wlas/ranking/topGainers?regionId=6&rankType=1d&pageIndex=1&pageSize=10"
WEBULL_PRE_MARKET_GAINERS_URL = "https://quotes-gw.webullfintech.com/api/wlas/ranking/topGainers?regionId=6&rankType=preMarket&pageIndex=1&pageSize=10"
WEBULL_AFTER_MARKET_GAINERS_URL = "https://quotes-gw.webullfintech.com/api/wlas/ranking/topGainers?regionId=6&rankType=afterMarket&pageIndex=1&pageSize=10"
WEBULL_TOP_LOSERS_URL = "https://quotes-gw.webullfintech.com/api/wlas/ranking/dropGainers?regionId=6&rankType=1d&pageIndex=1&pageSize=10"
WEBULL_AFTER_MARKET_LOSERS_URL = "https://quotes-gw.webullbroker.com/api/wlas/ranking/dropGainers?regionId=6&rankType=afterMarket&pageIndex=1&pageSize=10"
WEBULL_QUOTE_1M_CHARTS_URL = "https://quotes-gw.webullbroker.com/api/quote/charts/query?tickerIds={}&type=m1&count={}&extendTrading=1"

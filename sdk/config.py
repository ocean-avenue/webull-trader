# https://alpaca.markets/docs/api-documentation/
APCA_DATA_URL = "https://data.alpaca.markets"
APCA_PAPER_API_BASE_URL = "https://paper-api.alpaca.markets"

# https://financialmodelingprep.com/developer/docs
FMP_API_BASE_URL = "https://financialmodelingprep.com/api/v3"

# https://finance.yahoo.com/gainers
YF_GAINERS_URL = "https://finance.yahoo.com/gainers?count=100"

# https://app.webull.com/market/region/6

WEBULL_DAILY_PL_URL = "https://ustrade.webullbroker.com/api/trading/v1/profitloss/account/period?dateRangeType=all&periodType=Day&secAccountId={}"

WEBULL_TICKER_QUOTE_URL = "https://quotes-gw.webullbroker.com/api/quotes/ticker/getTickerRealTime?tickerId={}&includeSecu=1&includeQuote=1"
WEBULL_TOP_GAINERS_URL = "https://quotes-gw.webullfintech.com/api/wlas/ranking/topGainers?regionId=6&rankType=1d&pageIndex=1&pageSize={}"
WEBULL_PRE_MARKET_GAINERS_URL = "https://quotes-gw.webullfintech.com/api/wlas/ranking/topGainers?regionId=6&rankType=preMarket&pageIndex=1&pageSize={}"
WEBULL_AFTER_MARKET_GAINERS_URL = "https://quotes-gw.webullfintech.com/api/wlas/ranking/topGainers?regionId=6&rankType=afterMarket&pageIndex=1&pageSize={}"
WEBULL_TOP_LOSERS_URL = "https://quotes-gw.webullfintech.com/api/wlas/ranking/dropGainers?regionId=6&rankType=1d&pageIndex=1&pageSize={}"
WEBULL_AFTER_MARKET_LOSERS_URL = "https://quotes-gw.webullbroker.com/api/wlas/ranking/dropGainers?regionId=6&rankType=afterMarket&pageIndex=1&pageSize={}"
WEBULL_PRE_MARKET_LOSERS_URL = "https://quotes-gw.webullfintech.com/api/wlas/ranking/dropGainers?regionId=6&rankType=preMarket&pageIndex=1&pageSize={}"
WEBULL_QUOTE_1M_CHARTS_URL = "https://quotes-gw.webullbroker.com/api/quote/charts/query?tickerIds={}&type=m1&count={}&extendTrading=1"

# https://finviz.com/quote.ashx?t=FB

FINVIZ_QUOTE_URL = "https://finviz.com/quote.ashx?t={}"

# https://finviz.com/screener.ashx

# Earning Day (Unusual Volume)
FINVIZ_EARNING_DAY_UNUSUAL_VOLUME_MID_CAP_URL = "https://finviz.com/screener.ashx?v=111&s=ta_unusualvolume&f=earningsdate_today,ta_perf_dup&ft=4"

# Unusual Volume (Mid Cap)
FINVIZ_UNUSUAL_VOLUME_MID_CAP_URL = "https://finviz.com/screener.ashx?v=211&s=ta_unusualvolume&f=cap_midunder,ind_stocksonly,ta_highlow20d_nh,ta_pattern_channelup&ft=4"

# Channel Up (Communication Services)
FINVIZ_CHANNEL_UP_COMMUNICATION_SERVICES_URL = "https://finviz.com/screener.ashx?v=111&f=sec_communicationservices,sh_avgvol_o500,ta_pattern_channelup2&ft=4"
# Channel Up (Energy)
FINVIZ_CHANNEL_UP_ENERGY_URL = "https://finviz.com/screener.ashx?v=111&f=sec_energy,sh_avgvol_o500,ta_pattern_channelup2&ft=4"
# Channel Up (Consumer Cyclical)
FINVIZ_CHANNEL_UP_CONSUMER_CYCLICAL_URL = "https://finviz.com/screener.ashx?v=111&f=sec_consumercyclical,sh_avgvol_o500,ta_pattern_channelup2&ft=4"
# Channel Up (Consumer Defensive)
FINVIZ_CHANNEL_UP_CONSUMER_DEFENSIVE_URL = "https://finviz.com/screener.ashx?v=111&f=sec_consumerdefensive,sh_avgvol_o500,ta_pattern_channelup2&ft=4"
# Channel Up (Technology)
FINVIZ_CHANNEL_UP_TECHNOLOGY_URL = "https://finviz.com/screener.ashx?v=111&f=sec_technology,sh_avgvol_o500,ta_pattern_channelup2&ft=4"

# Double Bottom (Communication Services)
FINVIZ_DOUBLE_BOTTOM_COMMUNICATION_SERVICES_URL = "https://finviz.com/screener.ashx?v=111&f=sec_energy,sh_avgvol_o500,ta_pattern_doublebottom&ft=4"
# Double Bottom (Energy)
FINVIZ_DOUBLE_BOTTOM_ENERGY_URL = "https://finviz.com/screener.ashx?v=111&f=sec_energy,sh_avgvol_o500,ta_pattern_doublebottom&ft=4"
# Double Bottom (Consumer Cyclical)
FINVIZ_DOUBLE_BOTTOM_CONSUMER_CYCLICAL_URL = "https://finviz.com/screener.ashx?v=111&f=sec_consumercyclical,sh_avgvol_o500,ta_pattern_doublebottom&ft=4"
# Double Bottom (Consumer Defensive)
FINVIZ_DOUBLE_BOTTOM_CONSUMER_DEFENSIVE_URL = "https://finviz.com/screener.ashx?v=111&f=sec_consumerdefensive,sh_avgvol_o500,ta_pattern_doublebottom&ft=4"
# Double Bottom (Technology)
FINVIZ_DOUBLE_BOTTOM_TECHNOLOGY_URL = "https://finviz.com/screener.ashx?v=111&f=sec_technology,sh_avgvol_o500,ta_pattern_doublebottom&ft=4"

import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup

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

# Large Cap with Major News
FINVIZ_MAJOR_NEWS_LARGE_CAP_URL = "https://finviz.com/screener.ashx?v=111&s=n_majornews&f=cap_largeover&o=marketcap"

EARNING_DAY_SCREENER = "earning_day"
UNUSUAL_VOLUME_SCREENER = "unusual_volume"
CHANNEL_UP_SCREENER = "channel_up"
DOUBLE_BOTTOM_SCREENER = "double_bottom"
MAJOR_NEWS_SCREENER = "major_news"

# screener url config
_EARNING_DAY_URLS = [
    FINVIZ_EARNING_DAY_UNUSUAL_VOLUME_MID_CAP_URL,
]
_UNUSUAL_VOLUME_URLS = [
    FINVIZ_UNUSUAL_VOLUME_MID_CAP_URL,
]
_CHANNEL_UP_URLS = [
    FINVIZ_CHANNEL_UP_ENERGY_URL,
    FINVIZ_CHANNEL_UP_TECHNOLOGY_URL,
]
_DOUBLE_BOTTOM_URLS = [
    FINVIZ_DOUBLE_BOTTOM_ENERGY_URL,
    FINVIZ_DOUBLE_BOTTOM_TECHNOLOGY_URL,
]
_MAJOR_NEWS_URLS = [
    FINVIZ_MAJOR_NEWS_LARGE_CAP_URL,
]


def _get_browser_headers():
    return {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.92 Safari/537.36",
        "referer": "https://finviz.com/",
        "Accept-Encoding": None,
    }


def get_quote(symbol):
    time.sleep(1)
    try:
        session = requests.Session()
        url = FINVIZ_QUOTE_URL.format(symbol)
        res = session.get(url, headers=_get_browser_headers())
        sp = BeautifulSoup(res.text, "html.parser")
        all_tr = sp.findAll("tr", {"class": "table-dark-row"})
        container = all_tr[2].findAll('td', {'class': 'snapshot-td2'})[4]
        if container.find("span"):
            short_float = container.find("span").contents[0].replace("%", "")
        else:
            short_float = container.contents[0].contents[0].replace("%", "")
        # parse news
        news = []
        news_table = sp.find("table", {"id": "news-table"})
        news_table_all_tr = news_table.findAll("tr")
        last_news_date = ""
        for news_table_tr in news_table_all_tr:
            news_date_str = news_table_tr.find(
                "td", {"align": "right"}).contents[0].strip()
            news_date_parts = news_date_str.split(" ")
            if len(news_date_parts) >= 2:
                last_news_date = news_date_parts[0]
            else:
                news_date_str = last_news_date + " " + news_date_str
            news_datetime = datetime.strptime(
                news_date_str, "%b-%d-%y %I:%M%p")
            news_link_a = news_table_tr.find(
                "a", {"class": "tab-link-news"}, href=True)
            title = news_link_a.contents[0]
            news_link = news_link_a["href"]
            source = news_table_tr.find(
                "span", {"style": "color:#aa6dc0;font-size:9px"}).contents[0].strip()
            news.append({
                "title": title,
                "source": source,
                "news_link": news_link,
                "news_time": news_datetime.strftime("%Y-%m-%d %H:%M:%S"),
            })
        return {
            "shortFloat": short_float,
            "news": news,
        }
    except:
        return {
            "shortFloat": None,
            "news": [],
        }


def fetch_screeners(screener_type):
    session = requests.Session()

    urls = []
    if screener_type == EARNING_DAY_SCREENER:
        urls = _EARNING_DAY_URLS
    elif screener_type == UNUSUAL_VOLUME_SCREENER:
        urls = _UNUSUAL_VOLUME_URLS
    elif screener_type == CHANNEL_UP_SCREENER:
        urls = _CHANNEL_UP_URLS
    elif screener_type == DOUBLE_BOTTOM_SCREENER:
        urls = _DOUBLE_BOTTOM_URLS
    elif screener_type == MAJOR_NEWS_SCREENER:
        urls = _MAJOR_NEWS_URLS
    else:
        # unknown screener type
        urls = []

    screened_list = []
    for url in urls:
        res = session.get(url, headers=_get_browser_headers())
        sp = BeautifulSoup(res.text, "html.parser")
        all_tr = sp.findAll("tr", {"class": "table-dark-row-cp"}) + \
            sp.findAll("tr", {"class": "table-light-row-cp"})
        for i in range(0, len(all_tr)):
            tr = all_tr[i]
            all_td = tr.findAll("td")
            symbol = all_td[1].find("a").contents[0]
            sector = all_td[3].find("a").contents[0]
            # mktcap = all_td[6].find("a").contents[0]
            # price = all_td[8].find("a").find("span").contents[0]
            # change = all_td[9].find("a").find("span").contents[0]
            # volume = all_td[10].find("a").contents[0].replace(",", "")
            screened_list.append({
                "symbol": symbol,
                "sector": sector,
                # "market_cap": mktcap,
                # "price": price,
                # "change": change,
                # "volume": volume,
            })
        time.sleep(1)

    return screened_list

# webull-trader

Day & Swing Trading System with Webull Platform

### Strategy:

Day Trading [[Momentum](https://www.warriortrading.com/momentum-day-trading-strategy/)]

Swing Trading [[Way of the turtle](https://zhuanlan.zhihu.com/p/34794101)]

### Get Started:

1. Install required packages:

```
$ pip install -r requirements.txt
```

2. Initial settings:

```
$ python manage.py shell < scripts/init_settings.py
```

3. Create webull credentials object and write cred data:

```
{"extInfo":{"userPwdFlag":"1"},"accessToken":"dc_us1.17935b94a81-b4595a91ffea4e4c9b23f64234b9d359","uuid":"178b7d31cf76e22059e78574d6cbbbc46561bde710d","refreshToken":"17935b94a81-c16495b415e44ea4bbee230d2ceed5ae","tokenExpireTime":"2021-05-11T04:53:26.273+0000","firstTimeOfThird":false,"registerAddress":6,"settings":{"id":434302726667792384,"userId":309094127,"regionId":6,"language":"en","focusMarketId":"2,3,4,5,6,14","theme":2,"increDecreColor":2,"fontSize":"M","portfolioDisplayMode":2,"portfolioNameNewline":1,"portfolioHoldingsDisplay":1,"portfolioIndexDisplay":1,"portfolioBulletin":1,"kdata":1,"refreshFrequency":1,"shock":0,"tickerPriceRemind":1,"orderDealRemind":1,"hotNews":1,"chartOption":2,"operateTime":"1969-12-31T00:00:00.000+0000","languageUpdateTime":"1970-01-01T00:00:00.000+0000","createTime":"2021-04-09T18:09:29.000+0000","updateTime":"2021-04-09T18:09:29.000+0000","listStyle":1}}
```

4. Run server:

```
$ python manage.py runserver
```

5. Run scheduler:

```
$ python manage.py runscheduler
```

### Deploy:

1. Run server:

```
$ uwsgi --ini uwsgi.ini --touch-reload /tmp/webull-trader/deploy.ini --logto /tmp/webull-trader/uwsgi.log
```

2. Hot reload:

```
$ touch /tmp/webull-trader/deploy.ini
```

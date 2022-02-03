# webull-trader

Day/Swing Trading System powered by Webull Platform

### Strategy:

Day Trading [[Breakout](https://github.com/quanturtleteam/webull-trader/blob/main/trading/day_breakout.py)] [[Grinding](https://github.com/quanturtleteam/webull-trader/blob/main/trading/day_grinding_largecap.py)] [[Momentum](https://github.com/quanturtleteam/webull-trader/blob/main/trading/day_momo.py)] [[Red to Green](https://github.com/quanturtleteam/webull-trader/blob/main/trading/day_redgreen.py)] [[VWAP Reclaim](https://github.com/quanturtleteam/webull-trader/blob/main/trading/day_vwap_largecap.py)]

Swing Trading [[Turtle](https://github.com/quanturtleteam/webull-trader/blob/main/trading/swing_turtle.py)]

### Get Started:

1. Install required packages:

```
pip install git+https://github.com/tedchou12/webull
pip install -r requirements.txt
```

2. Run initialize script:

```
python manage.py shell < scripts/initialize.py
```

3. Create webull credentials object and write cred data, trade password.

4. Run server:

```
python manage.py runserver
```

5. Run scheduler:

```
python manage.py runscheduler
```

### Commands:

1. Run stats data:

```
python manage.py runstatsdata 2021-12-31
```

2. Run amend trades:

```
python manage.py runamendtrades
```

### Backtest:

1. Run backtest command:

```
python manage.py shell < backtest/executor.py
```

### Deploy:

1. Run server:

```
screen -r server
```
```
uwsgi --ini uwsgi.ini --enable-threads
```

2. Run scheduler:

```
screen -r scheduler
```
```
python manage.py runscheduler
```

3. Hot reload:

```
touch /tmp/deploy.ini
```
```
uwsgi --ini uwsgi.ini --touch-reload /tmp/deploy.ini --logto /tmp/uwsgi.log
```

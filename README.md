# webull-trader

Day/Swing Trading System powered by Webull Platform

### Strategy:

Day Trading [[Momentum](https://www.warriortrading.com/momentum-day-trading-strategy/)] [[R-to-G](https://community.humbledtrader.com/products/video-library/categories/4074208/posts/13662620)]

Swing Trading [[Way of the turtle](https://zhuanlan.zhihu.com/p/34794101)]

### Get Started:

1. Install required packages:

```
pip install -r requirements.txt
```

2. Initialize:

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

### Deploy:

1. Run server:

```
screen -r server
```
```
uwsgi --ini uwsgi.ini --touch-reload /tmp/deploy.ini --logto /tmp/uwsgi.log
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

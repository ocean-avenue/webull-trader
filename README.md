# old-ross
Day trading system with Webull (only pre/after market)

### Strategy:
[Gap and Go](https://www.warriortrading.com/gap-go/)

[Bull Flag](https://www.warriortrading.com/bull-flag-trading/)

### Get Started:

1. Install required packages:

```
$ pip install -r requirements.txt
```

2. Initial settings:

```
$ python manage.py shell < scripts/init_settings.py
```

3. Create webull credentials object and copy cred data from webull account.

4. Run server:

```
$ python manage.py runserver
```

5. Run scheduler:

```
$ python manage.py runscheduler
```

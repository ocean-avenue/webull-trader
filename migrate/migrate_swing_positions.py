# -*- coding: utf-8 -*-

# create swing positions


def start():

    from datetime import date
    from django.utils import timezone
    from webull_trader.models import SwingPosition
    from webull_trader.enums import SetupType
    from scripts import utils

    SWING_POSITIONS = [
        {
            "symbol": "ARKK",
            "order_id": "463586362793170944",
            "setup": SetupType.SWING_55_DAYS_NEW_HIGH,
            "cost": 129.16,
            "quantity": 1,
        },
        {
            "symbol": "ARKQ",
            "order_id": "463586375166337024",
            "setup": SetupType.SWING_55_DAYS_NEW_HIGH,
            "cost": 86.39,
            "quantity": 2,
        },
        {
            "symbol": "ARKG",
            "order_id": "463586391188574208",
            "setup": SetupType.SWING_55_DAYS_NEW_HIGH,
            "cost": 92.36,
            "quantity": 2,
        },
        {
            "symbol": "EH",
            "order_id": "463586521098786816",
            "setup": SetupType.SWING_55_DAYS_NEW_HIGH,
            "cost": 42.58,
            "quantity": 4,
        },
        {
            "symbol": "FUTU",
            "order_id": "463586554074398720",
            "setup": SetupType.SWING_55_DAYS_NEW_HIGH,
            "cost": 176.46,
            "quantity": 1,
        },
        {
            "symbol": "JKS",
            "order_id": "463586638837092352",
            "setup": SetupType.SWING_55_DAYS_NEW_HIGH,
            "cost": 53.5,
            "quantity": 3,
        },
        {
            "symbol": "NIO",
            "order_id": "463586714699440128",
            "setup": SetupType.SWING_55_DAYS_NEW_HIGH,
            "cost": 48.91,
            "quantity": 4,
        },
        {
            "symbol": "PTON",
            "order_id": "463586786350778368",
            "setup": SetupType.SWING_55_DAYS_NEW_HIGH,
            "cost": 123.34,
            "quantity": 1,
        },
    ]

    for swing_position in SWING_POSITIONS:
        position = SwingPosition.objects.filter(
            symbol=swing_position["symbol"]).first()
        if not position:
            position = SwingPosition(symbol=swing_position["symbol"])
        position.symbol = swing_position["symbol"]
        position.order_ids = swing_position["order_id"]
        position.total_cost = swing_position["cost"] * swing_position["quantity"]
        position.quantity = swing_position["quantity"]
        position.setup = swing_position["setup"]
        position.buy_time = timezone.now()
        position.buy_date = date.today()
        position.save()

    print("[{}] Migrate {} positions done".format(
        utils.get_now(), len(SWING_POSITIONS)))


if __name__ == "django.core.management.commands.shell":
    start()

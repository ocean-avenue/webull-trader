# -*- coding: utf-8 -*-

# fill order note with correct setup


def start():
    from webull_trader.models import WebullOrderNote
    from webull_trader.enums import SetupType, AlgorithmType
    from scripts import utils

    setup_type = SetupType.DAY_FIRST_CANDLE_NEW_HIGH
    algo_type = utils.get_algo_type()
    if algo_type == AlgorithmType.DAY_BREAKOUT:
        setup_type = SetupType.DAY_20_MINUTES_NEW_HIGH
    elif algo_type == AlgorithmType.DAY_RED_TO_GREEN:
        setup_type = SetupType.DAY_RED_TO_GREEN
    elif algo_type == AlgorithmType.DAY_EARNINGS:
        setup_type = SetupType.DAY_EARNINGS_GAP
    elif algo_type == AlgorithmType.SWING_TURTLE_20:
        setup_type = SetupType.SWING_20_DAYS_NEW_HIGH
    elif algo_type == AlgorithmType.SWING_TURTLE_55:
        setup_type = SetupType.SWING_55_DAYS_NEW_HIGH
    order_notes = WebullOrderNote.objects.all()
    for order_note in order_notes:
        order_note.setup = setup_type
        order_note.save()

    print("[{}] Migrate {} order notes setup done".format(
        utils.get_now(), len(order_notes)))


if __name__ == "django.core.management.commands.shell":
    start()

# -*- coding: utf-8 -*-

# export orders from webull account to csv file

def start():
    from sdk import webullsdk
    from scripts import utils
    from old_ross.models import TradingSettings

    trading_settings = TradingSettings.objects.first()
    if not trading_settings:
        print("[{}] Cannot find trading settings, exit!".format(utils.get_now()))
        return

    webullsdk.login(paper=trading_settings.paper)

    history_orders = webullsdk.get_history_orders(
        status='Filled', count=1000)[::-1]

    export_day = history_orders[-1]['filledTime'].split(" ")[0]

    today_orders = []

    for order in history_orders:
        filled_day = order['filledTime'].split(" ")[0]
        if export_day == filled_day:
            today_orders.append(order)

    # output csv for now
    output_file_name = "Webull_Orders_Records_{}.csv".format(
        export_day.replace("/", "_"))
    output = open(output_file_name, "w")
    # write header
    output.write(
        "Name,Symbol,Side,Status,Filled,Total Qty,Price,Avg Price,Time-in-Force,Placed Time,Filled Time\n")
    for order in today_orders:
        output.write("{},{},{},{},{},{},{},{},{},{},{}".format(
            order['ticker']['name'],
            order['ticker']['symbol'],
            order['action'],
            order['status'],
            order['filledQuantity'],
            order['totalQuantity'],
            order['avgFilledPrice'],
            order['avgFilledPrice'],
            order['timeInForce'],
            order['placedTime'],
            order['filledTime'],
        ))
        output.write("\n")
    output.close()


if __name__ == "django.core.management.commands.shell":
    start()

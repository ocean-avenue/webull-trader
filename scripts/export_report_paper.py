# -*- coding: utf-8 -*-


def start():
    from datetime import datetime
    from sdk import webullsdk

    webullsdk.login(paper=True)

    history_orders = webullsdk.get_history_orders(
        status='Filled', count=1000)[::-1]

    today = datetime.today().strftime("%m/%d/%Y")
    today_orders = []

    for order in history_orders:
        filled_day = order['filledTime'].split(" ")[0]
        if today == filled_day:
            today_orders.append(order)

    # output csv for now
    output_file_name = "Webull_Orders_Records_{}_{}_{}.csv".format(
        datetime.today().year, datetime.today().month, datetime.today().day)
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

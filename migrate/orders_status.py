# -*- coding: utf-8 -*-

# fetch orders from webull account into database

# class StatusType:
#     FILLED = 0
#     CANCELLED = 1
#     PARTIALLY_FILLED = 2
#     FAILED = 3
#     WORKING = 4
#     PENDING = 5
#     @staticmethod
#     def tostr(val):
#         if val == StatusType.FILLED:
#             return 'FILLED'
#         if val == StatusType.CANCELLED:
#             return 'CANCELLED'
#         if val == StatusType.PARTIALLY_FILLED:
#             return 'PARTIALLY_FILLED'
#         if val == StatusType.FAILED:
#             return 'FAILED'
#         if val == StatusType.WORKING:
#             return 'WORKING'
#         if val == StatusType.PENDING:
#             return 'PENDING'
#         return UNKNOWN
#
# def get_order_status_enum(status_str):
#     status = enums.StatusType.FILLED
#     if status_str == "Cancelled":
#         status = enums.StatusType.CANCELLED
#     elif status_str == "Working":
#         status = enums.StatusType.WORKING
#     elif status_str == "Pending":
#         status = enums.StatusType.PENDING
#     elif status_str == "Failed":
#         status = enums.StatusType.FAILED
#     return status

def start():
    from webull_trader.models import WebullOrder
    from common import utils

    orders = WebullOrder.objects.all()

    for order in orders:
        if order.status == "0":
            order.status = "Filled"
            order.save()
        elif order.status == "1":
            order.status = "Cancelled"
            order.save()
        elif order.status == "2":
            order.status = "Partially Filled"
            order.save()
        elif order.status == "3":
            order.status = "Failed"
            order.save()
        elif order.status == "4":
            order.status = "Working"
            order.save()
        elif order.status == "5":
            order.status = "Pending"
            order.save()

    print("[{}] Migrate {} orders status done".format(
        utils.get_now(), len(orders)))


if __name__ == "django.core.management.commands.shell":
    start()

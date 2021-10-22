from common import utils, db
from sdk import webullsdk
from webull_trader.models import WebullOrder


# Order tracker class
class OrderTracker:

    def __init__(self, paper=True):
        self.paper = paper
        self.current_orders = {}

    def _order_done(self, status):
        if status == webullsdk.ORDER_STATUS_CANCELED or status == webullsdk.ORDER_STATUS_FILLED or \
                status == webullsdk.ORDER_STATUS_PARTIALLY_FILLED or status == webullsdk.ORDER_STATUS_FAILED:
            return True
        return False

    def start_tracking(self, order_response, setup, note=None):
        order_id = utils.get_order_id_from_response(
            order_response, paper=self.paper)
        if order_id:
            self.current_orders[order_id] = {
                # 'status': webullsdk.ORDER_STATUS_PENDING,
                'setup': setup,
                'note': note,
            }

    def update_orders(self):
        if len(self.current_orders) > 0:
            orders = webullsdk.get_history_orders(count=20)

            for order_data in orders:
                # save order to db
                db.save_webull_order(order_data, self.paper)

            for order_id in list(self.current_orders):
                order = WebullOrder.objects.filter(order_id=order_id).first()
                if order:
                    # order done
                    if self._order_done(order.status):
                        open_order = self.current_orders[order_id]
                        # update setup
                        order.setup = open_order['setup']
                        # update note
                        order.note = open_order['note']
                        order.save()
                        # remove from open orders
                        del self.current_orders[order_id]
from typing import Optional, Tuple
from common import db
from common.enums import SetupType
from sdk import webullsdk
from webull_trader.models import WebullOrder


# Order tracker class
class OrderTracker:

    def __init__(self, paper: bool = True):
        self.paper: bool = paper
        self.current_orders: dict = {}

    def _order_done(self, status: str) -> bool:
        if status == webullsdk.ORDER_STATUS_CANCELED or status == webullsdk.ORDER_STATUS_FILLED or \
                status == webullsdk.ORDER_STATUS_PARTIALLY_FILLED or status == webullsdk.ORDER_STATUS_FAILED:
            return True
        return False

    def start_tracking(self, order_id: str, setup: SetupType, note: Optional[str] = None, retry_after_cancel: Optional[bool] = None, retry_limit: Optional[int] = None):
        if order_id in self.current_orders:
            self.current_orders[order_id]['setup'] = setup
            if note != None:
                self.current_orders[order_id]['note'] = note
            if retry_after_cancel != None:
                self.current_orders[order_id]['retry_after_cancel'] = retry_after_cancel
            if retry_limit != None:
                self.current_orders[order_id]['retry_limit'] = retry_limit
        else:
            self.current_orders[order_id] = {
                # 'status': webullsdk.ORDER_STATUS_PENDING,
                'setup': setup,
                'note': note or "",
                'retry_after_cancel': retry_after_cancel or False,
                'retry_limit': retry_limit or 0,
            }

    def check_retry_after_cancel(self, order_id) -> Tuple[bool, int]:
        if order_id in self.current_orders:
            open_order = self.current_orders[order_id]
            return (open_order['retry_after_cancel'], open_order['retry_limit'])
        return (False, 0)

    def stop_tracking(self, order_id: str):
        if order_id in self.current_orders:
            del self.current_orders[order_id]

    def get_order(self, order_id: str) -> Optional[WebullOrder]:
        return WebullOrder.objects.filter(order_id=order_id).first()

    def update_orders(self):
        if len(self.current_orders) > 0:
            orders = webullsdk.get_history_orders(count=50)

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

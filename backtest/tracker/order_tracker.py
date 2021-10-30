
class BacktestOrderTracker:

    def __init__(self):
        self.order_id = 100000

    def get_next_order_id(self):
        order_id = self.order_id
        self.order_id += 1
        return order_id

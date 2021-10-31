
_order_id: int = 100000

def get_next_order_id() -> int:
    global _order_id
    _order_id += 1
    return _order_id

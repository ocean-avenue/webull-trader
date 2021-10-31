
INIT_BALANCE: float = 30000.0

_balance: float = INIT_BALANCE


def get_balance() -> float:
    global _balance
    return _balance


def update_balance(change: float):
    global _balance
    _balance = round(_balance + change, 2)


def get_total_pl() -> float:
    return round(_balance - INIT_BALANCE, 2)


def get_total_pl_rate() -> float:
    return round((_balance - INIT_BALANCE) / INIT_BALANCE, 2)

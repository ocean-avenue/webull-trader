
class BacktestAccountTracker:

    def __init__(self, balance: float):
        self.balance = balance

    def get_cash_balance(self) -> float:
        return self.balance

    def update_cash_balance(self, change: float):
        self.balance = round(self.balance + change, 2)

from typing import Optional
from sdk import webullsdk
from trading.tracker.trading_tracker import TrackingTicker


# Position tracker class
class PositionTracker:

    def __init__(self, paper: bool = True):
        self.paper: bool = paper
        self.current_positions: dict = {}

    def get_position(self, ticker: TrackingTicker) -> Optional[dict]:
        ticker_id = ticker.get_id()
        if ticker_id in self.current_positions:
            return self.current_positions[ticker_id]
        return None

    def update_positions(self):
        # reset
        self.current_positions.clear()
        positions = webullsdk.get_positions()
        if not positions:
            return
        # update
        for position in positions:
            ticker_id = str(position['ticker']['tickerId'])
            self.current_positions[ticker_id] = position

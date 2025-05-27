import random
from datetime import datetime, timedelta, timezone
from faker import Faker

fake = Faker()

SYMBOLS = ["AAPL", "MSFT", "GOOG", "TSLA", "NVDA", "META"]
SIDES = ["BUY", "SELL"]

# Generate a random trade for booking
def random_trade():
    ts = datetime.now(timezone.utc) - timedelta(seconds=random.randint(0, 3600))
    return {
        "symbol": random.choice(SYMBOLS),
        "side": random.choice(SIDES),
        "qty": round(random.uniform(10, 1000), 2),
        "price": round(random.uniform(100, 1000), 2),
        "trade_ts": ts.isoformat()
    }

# Simulate counterparties from booked trades
def generate_counterparty(trades):
    simulated = []
    for t in trades:
        chance = random.random()
        if chance < 0.75:  # 75% chance it gets copied
            trade = t.copy()
            if random.random() < 0.25:  # 25% chance of altering quantity
                delta = random.randint(-20, 20)
                trade["qty"] += delta
                trade["qty"] = max(1, trade["qty"])
            simulated.append(trade)
    return simulated

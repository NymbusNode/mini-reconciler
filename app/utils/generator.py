from faker import Faker
import random
from decimal import Decimal
from datetime import datetime, timedelta

fake = Faker()

def random_trade():
    symbol = random.choice(["AAPL", "MSFT", "NVDA", "META", "TSLA"])
    side   = random.choice(["BUY", "SELL"])
    qty    = Decimal(random.randint(1, 1000))
    price  = Decimal(round(random.uniform(50, 1000), 2))
    ts     = datetime.utcnow() - timedelta(seconds=random.randint(0, 3600))
    return dict(symbol=symbol, side=side, qty=qty, price=price, trade_ts=ts)

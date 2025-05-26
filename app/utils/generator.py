from faker import Faker
import random
from datetime import datetime, timedelta, timezone

fake = Faker()

def random_trade() -> dict:
    """Return one synthetic trade in a format gRPC/Protobuf can encode."""
    symbol = random.choice(["AAPL", "MSFT", "NVDA", "META", "TSLA"])
    side   = random.choice(["BUY", "SELL"])

    qty    = float(random.randint(1, 1000))         
    price  = float(round(random.uniform(50, 1_000), 2))           

    ts = (
        datetime.now(timezone.utc) -
        timedelta(seconds=random.randint(0, 3_600))
    ).isoformat()                                                

    return {
        "symbol":   symbol,
        "side":     side,
        "qty":      qty,
        "price":    price,
        "trade_ts": ts,
    }

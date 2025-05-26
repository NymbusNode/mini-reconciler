import asyncio
from app.utils.generator import random_trade
from app.service import client as grpc_client

async def main():
    trades = [random_trade() for _ in range(50)]
    inserted = await grpc_client.ingest_trades(trades)
    print(f"Seeded {inserted} trades.")

if __name__ == "__main__":
    asyncio.run(main())

"""
Fast gRPC service implementing:
• Trade ingestion
• Simulated counterparty trades
• Professional break detection
• Position recalculation
"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from concurrent import futures
import random
import sys

import grpc
from grpc_tools import protoc
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import async_session, engine
from app import models

# ------------------- compile protobuf -------------------
PROTO_DIR = Path(__file__).resolve().parent.parent.parent / "proto"
GEN_DIR = PROTO_DIR / "generated"
GEN_DIR.mkdir(exist_ok=True)
if not (GEN_DIR / "reconcile_pb2.py").exists():
    protoc.main([
        "protoc",
        f"-I{PROTO_DIR}",
        f"--python_out={GEN_DIR}",
        f"--grpc_python_out={GEN_DIR}",
        str(PROTO_DIR / "reconcile.proto"),
    ])

sys.path.append(str(GEN_DIR))
import reconcile_pb2 as pb2  # type: ignore
import reconcile_pb2_grpc as pb2_grpc  # type: ignore

# ------------------- utils -------------------
async def _init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

def _simulate_counterparty(trades: list[models.Trade]) -> list[models.CounterpartyTrade]:
    """Copy 90 % of trades; 10 % are missing; 10 % of copied trades get qty tweak."""
    cp = []
    for t in trades:
        if random.random() >= 0.90:  # missing 10 %
            continue
        new_qty = t.qty
        if random.random() < 0.10:  # alter qty 10 % of included trades
            delta = random.randint(-20, 20)
            new_qty = max(1, t.qty + delta)
        cp.append(
            models.CounterpartyTrade(
                trade_id=t.trade_id,
                symbol=t.symbol,
                side=t.side,
                qty=new_qty,
                price=t.price,
                trade_ts=t.trade_ts,
            )
        )
    return cp

async def _recalc_positions(session: AsyncSession):
    sql = text(
        """
        INSERT INTO positions(symbol, net_qty, vwap)
        SELECT symbol,
               SUM(CASE side WHEN 'BUY' THEN qty ELSE -qty END) AS net_qty,
               SUM(price * qty)::numeric / NULLIF(SUM(qty),0)  AS vwap
        FROM trades
        GROUP BY symbol
        ON CONFLICT(symbol) DO UPDATE
        SET net_qty = EXCLUDED.net_qty,
            vwap    = EXCLUDED.vwap;
        """
    )
    await session.execute(sql)

async def _detect_breaks(session: AsyncSession):
    await session.execute(text("DELETE FROM breaks"))  # clear old breaks for simplicity
    # quantity mismatches
    qty_sql = text(
        """
        INSERT INTO breaks(trade_id, reason)
        SELECT t.trade_id,
               CASE WHEN cp.qty > t.qty THEN 'Quantity Mismatch: Overstated'
                    ELSE 'Quantity Mismatch: Understated' END
        FROM trades t
        JOIN counterparty_trades cp USING(trade_id)
        WHERE t.qty <> cp.qty;
        """
    )
    await session.execute(qty_sql)

    missing_sql = text(
        """
        INSERT INTO breaks(trade_id, reason)
        SELECT t.trade_id, 'Missing Trade'
        FROM trades t
        LEFT JOIN counterparty_trades cp USING(trade_id)
        WHERE cp.trade_id IS NULL;
        """
    )
    await session.execute(missing_sql)

# ------------------- gRPC service -------------------
class ReconcileService(pb2_grpc.ReconcileServiceServicer):
    async def IngestTrades(self, request_iterator, context):
        async with async_session() as session:
            booked: list[models.Trade] = []
            async for t in request_iterator:
                booked.append(
                    models.Trade(
                        symbol=t.symbol,
                        side=t.side,
                        qty=t.qty,
                        price=t.price,
                        trade_ts=datetime.fromisoformat(t.trade_ts),
                    )
                )
            session.add_all(booked)
            await session.flush()  # assign IDs

            # simulate counterparty trades
            cps = _simulate_counterparty(booked)
            session.add_all(cps)

            # recalc positions & breaks
            await session.flush()
            await _recalc_positions(session)
            await _detect_breaks(session)
            await session.commit()

        return pb2.IngestResponse(inserted=len(booked))

    async def GetPositions(self, request, context):
        async with async_session() as session:
            rows = (await session.execute(select(models.Position))).scalars().all()
            return pb2.Positions(
                items=[pb2.Position(symbol=r.symbol, net_qty=float(r.net_qty), vwap=float(r.vwap)) for r in rows]
            )

    async def GetBreaks(self, request, context):
        async with async_session() as session:
            rows = (await session.execute(select(models.Break))).scalars().all()
            return pb2.Breaks(
                items=[pb2.Break(trade_id=r.trade_id, reason=r.reason, detected_ts=r.detected_ts.isoformat()) for r in rows]
            )

async def serve():
    await _init_db()
    server = grpc.aio.server(futures.ThreadPoolExecutor())
    pb2_grpc.add_ReconcileServiceServicer_to_server(ReconcileService(), server)
    server.add_insecure_port("0.0.0.0:50051")
    await server.start()
    print("gRPC server running on 0.0.0.0:50051")
    await server.wait_for_termination()

if __name__ == "__main__":
    asyncio.run(serve())
"""
app/service/server.py
gRPC service for the Mini Post-Trade Reconciler
"""

import asyncio
import datetime
from concurrent import futures
from pathlib import Path
import sys

import grpc
from grpc_tools import protoc
from sqlalchemy import select, func, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import async_session, engine
from app import models

# --------------------------------------------------------------------------- #
# Compile protobuf stubs on-the-fly (only the first time)                     #
# --------------------------------------------------------------------------- #
PROTO_DIR = Path(__file__).resolve().parent.parent.parent / "proto"
GEN_DIR   = PROTO_DIR / "generated"
GEN_DIR.mkdir(exist_ok=True)

if not (GEN_DIR / "reconcile_pb2.py").exists():
    protoc.main(
        [
            "protoc",
            f"-I{PROTO_DIR}",
            f"--python_out={GEN_DIR}",
            f"--grpc_python_out={GEN_DIR}",
            str(PROTO_DIR / "reconcile.proto"),
        ]
    )

sys.path.append(str(GEN_DIR))
import reconcile_pb2 as pb2
import reconcile_pb2_grpc as pb2_grpc

# --------------------------------------------------------------------------- #
# Helper SQL routines                                                         #
# --------------------------------------------------------------------------- #
async def recalc_positions(session: AsyncSession) -> None:
    """
    Aggregate trades into the positions table (UPSERT).
    """
    agg_sql = text(
        """
        SELECT
            symbol,
            SUM(CASE side WHEN 'BUY' THEN qty ELSE -qty END)  AS net_qty,
            SUM(price * qty) / NULLIF(SUM(qty), 0)            AS vwap
        FROM trades
        GROUP BY symbol
        """
    )
    result = await session.execute(agg_sql)

    for symbol, net_qty, vwap in result.fetchall():
        stmt = (
            insert(models.Position)
            .values(symbol=symbol, net_qty=net_qty, vwap=vwap)
            .on_conflict_do_update(
                index_elements=["symbol"],
                set_={"net_qty": net_qty, "vwap": vwap},
            )
        )
        await session.execute(stmt)


async def detect_breaks(session: AsyncSession) -> None:
    """
    Insert a break for any trade that causes a negative position.
    """
    neg_sql = text(
        """
        INSERT INTO breaks (trade_id, reason)
        SELECT t.trade_id, 'Negative position'
        FROM trades t
        JOIN positions p USING (symbol)
        WHERE p.net_qty < 0
          AND NOT EXISTS (
              SELECT 1
              FROM breaks b
              WHERE b.trade_id = t.trade_id
                AND b.reason   = 'Negative position'
          )
        """
    )
    await session.execute(neg_sql)

# --------------------------------------------------------------------------- #
# gRPC service implementation                                                 #
# --------------------------------------------------------------------------- #
class ReconcileService(pb2_grpc.ReconcileServiceServicer):
    async def _insert_trade(self, session: AsyncSession, trade: pb2.Trade) -> None:
        """
        Convert protobuf Trade to ORM model and stage for insert.
        """
        session.add(
            models.Trade(
                symbol=trade.symbol,
                side=trade.side,
                qty=trade.qty,
                price=trade.price,
                trade_ts=datetime.datetime.fromisoformat(trade.trade_ts),
            )
        )

    # ------------- RPC methods --------------------------------------------- #
    async def IngestTrades(self, request_iterator, context):
        inserted = 0
        async with async_session() as session:
            async for trade in request_iterator:
                await self._insert_trade(session, trade)
                inserted += 1

            # post-processing
            await recalc_positions(session)
            await detect_breaks(session)

            await session.commit()

        return pb2.IngestResponse(inserted=inserted)

    async def GetPositions(self, request, context):
        async with async_session() as session:
            res = await session.execute(select(models.Position))
            positions = [
                pb2.Position(
                    symbol=row.symbol,
                    net_qty=float(row.net_qty),
                    vwap=float(row.vwap),
                )
                for row in res.scalars()
            ]
        return pb2.Positions(items=positions)

    async def GetBreaks(self, request, context):
        async with async_session() as session:
            res = await session.execute(select(models.Break))
            breaks = [
                pb2.Break(
                    trade_id=row.trade_id,
                    reason=row.reason,
                    detected_ts=row.detected_ts.isoformat(),
                )
                for row in res.scalars()
            ]
        return pb2.Breaks(items=breaks)


# --------------------------------------------------------------------------- #
# Server bootstrap                                                            #
# --------------------------------------------------------------------------- #
async def init_db() -> None:
    """Create all tables (idempotent)."""
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)


async def serve() -> None:
    await init_db()

    server = grpc.aio.server(futures.ThreadPoolExecutor())
    pb2_grpc.add_ReconcileServiceServicer_to_server(ReconcileService(), server)
    server.add_insecure_port("0.0.0.0:50051")

    await server.start()
    print("gRPC server running on 0.0.0.0:50051")
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())


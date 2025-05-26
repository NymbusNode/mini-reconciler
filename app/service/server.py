import asyncio, os, pathlib, datetime
from concurrent import futures

import grpc
from grpc_tools import protoc

# Dynamically compile proto if not generated
PROTO_PATH = pathlib.Path(__file__).parent.parent.parent / "proto"
GENERATED_PATH = PROTO_PATH / "generated"
GENERATED_PATH.mkdir(exist_ok=True)

if not (GENERATED_PATH / "reconcile_pb2.py").exists():
    protoc.main([
        "protoc",
        f"-I{PROTO_PATH}",
        f"--python_out={GENERATED_PATH}",
        f"--grpc_python_out={GENERATED_PATH}",
        str(PROTO_PATH / "reconcile.proto")
    ])

import sys
sys.path.append(str(GENERATED_PATH))

import reconcile_pb2 as pb2
import reconcile_pb2_grpc as pb2_grpc

from app.db import async_session, engine
from app import models
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

class ReconcileService(pb2_grpc.ReconcileServiceServicer):
    async def IngestTrades(self, request_iterator, context):
        inserted = 0
        async with async_session() as session:
            async for trade in request_iterator:
                inserted += 1
                await self._insert_trade(session, trade)
            await session.commit()
        return pb2.IngestResponse(inserted=inserted)

    async def _insert_trade(self, session: AsyncSession, trade):
        t = models.Trade(
            symbol = trade.symbol,
            side   = trade.side,
            qty    = trade.qty,
            price  = trade.price,
            trade_ts = datetime.datetime.fromisoformat(trade.trade_ts)
        )
        session.add(t)

    async def GetBreaks(self, request, context):
        async with async_session() as session:
            res = await session.execute(select(models.Break))
            breaks = []
            for row in res.scalars():
                breaks.append(pb2.Break(
                    trade_id=row.trade_id,
                    reason=row.reason,
                    detected_ts=row.detected_ts.isoformat()
                ))
            return pb2.Breaks(items=breaks)

    async def GetPositions(self, request, context):
        async with async_session() as session:
            res = await session.execute(select(models.Position))
            positions = []
            for row in res.scalars():
                positions.append(pb2.Position(
                    symbol=row.symbol,
                    net_qty=float(row.net_qty),
                    vwap=float(row.vwap),
                ))
            return pb2.Positions(items=positions)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

async def serve():
    await init_db()
    server = grpc.aio.server()
    pb2_grpc.add_ReconcileServiceServicer_to_server(ReconcileService(), server)
    server.add_insecure_port("[::]:50051")
    await server.start()
    print("gRPC server running on 0.0.0.0:50051")
    await server.wait_for_termination()

if __name__ == "__main__":
    asyncio.run(serve())

import os, pathlib, sys, grpc
from grpc_tools import protoc

GRPC_TARGET = os.getenv("GRPC_SERVER", "localhost:50051")

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

sys.path.append(str(GENERATED_PATH))
import reconcile_pb2 as pb2
import reconcile_pb2_grpc as pb2_grpc

async def ingest_trades(trades):
    async with grpc.aio.insecure_channel(GRPC_TARGET) as channel:
        stub = pb2_grpc.ReconcileServiceStub(channel)
        async def generator():
            for t in trades:
                yield pb2.Trade(**t)
        resp = await stub.IngestTrades(generator())
        return resp.inserted

async def get_positions():
    async with grpc.aio.insecure_channel(GRPC_TARGET) as channel:
        stub = pb2_grpc.ReconcileServiceStub(channel)
        res = await stub.GetPositions(pb2.Empty())
        return res.items

async def get_breaks():
    async with grpc.aio.insecure_channel(GRPC_TARGET) as channel:
        stub = pb2_grpc.ReconcileServiceStub(channel)
        res = await stub.GetBreaks(pb2.Empty())
        return res.items

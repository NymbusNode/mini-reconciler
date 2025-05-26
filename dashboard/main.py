from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import asyncio
from app.service import client as grpc_client  # reusing gRPC client

app = FastAPI()
app.mount("/static", StaticFiles(directory="dashboard/static"), name="static")
templates = Jinja2Templates(directory="dashboard/templates")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    positions = await grpc_client.get_positions()
    breaks = await grpc_client.get_breaks()
    return templates.TemplateResponse("index.html", {"request": request, "positions": positions, "breaks": breaks})

@app.post("/ingest")
async def ingest():
    from app.utils.generator import random_trade
    trades = [random_trade() for _ in range(50)]
    await grpc_client.ingest_trades(trades)
    return RedirectResponse(url="/", status_code=303)

@app.get("/positions", response_class=HTMLResponse)
async def refresh_positions(request: Request):
    positions = await grpc_client.get_positions()
    return templates.TemplateResponse("_positions.html", {"request": request, "positions": positions})

@app.get("/breaks", response_class=HTMLResponse)
async def refresh_breaks(request: Request):
    breaks = await grpc_client.get_breaks()
    return templates.TemplateResponse("_breaks.html", {"request": request, "breaks": breaks})
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from app.db import async_session
from app import models
from app.service import client as grpc_client  # reuse the gRPC helper – avoids proto import issues

app = FastAPI()
app.mount("/static", StaticFiles(directory="dashboard/static"), name="static")
templates = Jinja2Templates(directory="dashboard/templates")

# ------------------ helper ------------------
async def _stats():
    async with async_session() as s:
        trades = (await s.execute(select(models.Trade))).scalars().all()
        breaks = (await s.execute(select(models.Break))).scalars().all()
        pnl = sum(float(t.qty) * float(t.price) for t in trades if t.trade_id not in {b.trade_id for b in breaks})
        return len(trades), len(breaks), round(pnl, 2)

# ------------------ main dashboard ------------------
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    async with async_session() as s:
        ctx = {
            "request": request,
            "trades": (await s.execute(select(models.Trade).order_by(models.Trade.trade_ts.desc()))).scalars().all(),
            "counterparty": (await s.execute(select(models.CounterpartyTrade).order_by(models.CounterpartyTrade.trade_ts.desc()))).scalars().all(),
            "breaks": (await s.execute(select(models.Break))).scalars().all(),
            "positions": (await s.execute(select(models.Position))).scalars().all(),
        }
    ctx["total_trades"], ctx["total_breaks"], ctx["pnl"] = await _stats()
    return templates.TemplateResponse("index.html", ctx)

# ------------------ ingest 50 trades ------------------
@app.post("/ingest")
async def ingest():
    from app.utils.generator import random_trade

    trades = [random_trade() for _ in range(50)]
    # call the same async helper used by the CLI – proto already compiled in that package
    await grpc_client.ingest_trades(trades)
    return RedirectResponse("/", status_code=303)

# ------------------ clear all tables ------------------
@app.post("/clear")
async def clear():
    async with async_session() as s:
        for tbl in [models.Break, models.Position, models.CounterpartyTrade, models.Trade]:
            await s.execute(tbl.__table__.delete())
        await s.commit()
    return RedirectResponse("/", status_code=303)

# ------------------ HTMX partials ------------------
@app.get("/partial/{name}", response_class=HTMLResponse)
async def partial(request: Request, name: str):
    async with async_session() as s:
        ctx = {"request": request}
        if name == "trades":
            ctx["trades"] = (await s.execute(select(models.Trade).order_by(models.Trade.trade_ts.desc()))).scalars().all()
            return templates.TemplateResponse("_trades.html", ctx)
        if name == "counterparty":
            ctx["counterparty"] = (await s.execute(select(models.CounterpartyTrade).order_by(models.CounterpartyTrade.trade_ts.desc()))).scalars().all()
            return templates.TemplateResponse("_counterparty.html", ctx)
        if name == "breaks":
            ctx["breaks"] = (await s.execute(select(models.Break))).scalars().all()
            return templates.TemplateResponse("_breaks.html", ctx)
        if name == "positions":
            ctx["positions"] = (await s.execute(select(models.Position))).scalars().all()
            return templates.TemplateResponse("_positions.html", ctx)
    return HTMLResponse("Not found", status_code=404)
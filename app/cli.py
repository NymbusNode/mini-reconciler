import asyncio
import typer
from rich.table import Table
from rich.console import Console

from app.utils.generator import random_trade
from app.service import client as grpc_client

app = typer.Typer(add_completion=False)
console = Console()

@app.command()
def ingest(count: int = typer.Argument(20, help="Number of random trades to ingest")):
    """Generate and send random trades to the gRPC service."""
    trades = [random_trade() for _ in range(count)]
    inserted = asyncio.run(grpc_client.ingest_trades(trades))
    console.print(f"[green]Inserted {inserted} trades[/green]")

@app.command()
def positions():
    """Display current net positions."""
    items = asyncio.run(grpc_client.get_positions())
    table = Table(title="Net Positions")
    table.add_column("Symbol")
    table.add_column("Net Qty", justify="right")
    table.add_column("VWAP", justify="right")
    for p in items:
        table.add_row(p.symbol, f"{p.net_qty:.2f}", f"{p.vwap:.2f}")
    console.print(table)

@app.command()
def breaks():
    """Show breaks detected by reconciliation."""
    items = asyncio.run(grpc_client.get_breaks())
    table = Table(title="Breaks", style="red")
    table.add_column("Trade ID")
    table.add_column("Reason")
    table.add_column("Detected")
    for b in items:
        table.add_row(str(b.trade_id), b.reason, b.detected_ts)
    console.print(table)

if __name__ == "__main__":
    app()

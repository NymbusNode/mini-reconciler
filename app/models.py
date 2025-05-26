from sqlalchemy import Column, Integer, Numeric, Text, TIMESTAMP, CheckConstraint
from sqlalchemy.sql import func
from app.db import Base

class Trade(Base):
    __tablename__ = "trades"

    trade_id = Column(Integer, primary_key=True, autoincrement=True)
    symbol   = Column(Text, nullable=False)
    side     = Column(Text, CheckConstraint("side IN ('BUY','SELL')"), nullable=False)
    qty      = Column(Numeric, nullable=False)
    price    = Column(Numeric, nullable=False)
    trade_ts = Column(TIMESTAMP(timezone=False), server_default=func.now())

class Break(Base):
    __tablename__ = "breaks"

    break_id    = Column(Integer, primary_key=True, autoincrement=True)
    trade_id    = Column(Integer)
    reason      = Column(Text, nullable=False)
    detected_ts = Column(TIMESTAMP(timezone=False), server_default=func.now())

class Position(Base):
    __tablename__ = "positions"

    symbol  = Column(Text, primary_key=True)
    net_qty = Column(Numeric, nullable=False)
    vwap    = Column(Numeric, nullable=False)

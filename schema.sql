-- Trades executed in the market
CREATE TABLE IF NOT EXISTS trades (
    trade_id    SERIAL PRIMARY KEY,
    symbol      TEXT        NOT NULL,
    side        TEXT        CHECK (side IN ('BUY','SELL')),
    qty         NUMERIC     NOT NULL,
    price       NUMERIC     NOT NULL,
    trade_ts    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Breaks detected during reconciliation
CREATE TABLE IF NOT EXISTS breaks (
    break_id    SERIAL PRIMARY KEY,
    trade_id    INT REFERENCES trades(trade_id),
    reason      TEXT        NOT NULL,
    detected_ts TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Net positions per symbol
CREATE TABLE IF NOT EXISTS positions (
    symbol  TEXT PRIMARY KEY,
    net_qty NUMERIC NOT NULL,
    vwap    NUMERIC NOT NULL
);

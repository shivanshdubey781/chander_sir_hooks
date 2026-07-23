import pandas as pd

def calculate_vwma(candles: list[dict], length: int = 20) -> pd.Series:
    """
    candles: list of dicts with keys close, volume, ordered oldest -> newest
    Matches Pine Script's ta.vwma(src, len):
        vwma = sum(close * volume, len) / sum(volume, len)
    """
    if not candles:
        return pd.Series(dtype=float)
        
    df = pd.DataFrame(candles)
    if "close" not in df.columns or "volume" not in df.columns:
        return pd.Series(dtype=float)

    pv = df["close"] * df["volume"]
    vol_sum = df["volume"].rolling(window=length).sum()
    
    # Protect against division by zero
    vwma = pv.rolling(window=length).sum() / vol_sum.replace(0, float('nan'))
    return vwma

def determine_state(candles: list[dict], length: int = 20) -> tuple[str, float, float]:
    """
    Returns (state, latest_vwma, latest_close)
    state is 'bullish', 'bearish', or 'neutral' (not enough data / no clear signal)
    Requires price cross AND VWMA slope to agree, per the theory.
    """
    if not candles or len(candles) < length:
        return "neutral", None, None

    vwma_series = calculate_vwma(candles, length)
    valid_vwma = vwma_series.dropna()
    if len(valid_vwma) < 2:
        return "neutral", None, None

    latest_close = float(candles[-1]["close"])
    vwma_now = float(vwma_series.iloc[-1])
    vwma_prev = float(vwma_series.iloc[-2])

    if pd.isna(vwma_now) or pd.isna(vwma_prev):
        return "neutral", None, None

    price_above = latest_close > vwma_now
    price_below = latest_close < vwma_now
    slope_up = vwma_now > vwma_prev
    slope_down = vwma_now < vwma_prev

    if price_above and slope_up:
        return "bullish", vwma_now, latest_close
    if price_below and slope_down:
        return "bearish", vwma_now, latest_close
    return "neutral", vwma_now, latest_close

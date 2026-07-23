import os
import pyotp
from datetime import datetime, timedelta

try:
    from SmartApi import SmartConnect
    HAS_SMARTAPI = True
except ImportError:
    HAS_SMARTAPI = False

# Global cached session
_smart_api_client = None

def get_angel_session():
    global _smart_api_client
    if _smart_api_client is not None:
        return _smart_api_client

    if not HAS_SMARTAPI:
        print("[ANGEL BROKER WARNING] smartapi-python not installed.")
        return None

    api_key = os.getenv("ANGEL_API_KEY")
    client_code = os.getenv("ANGEL_CLIENT_CODE")
    password = os.getenv("ANGEL_PASSWORD")
    totp_key = os.getenv("ANGEL_TOTP_KEY")

    if not all([api_key, client_code, password, totp_key]):
        print("[ANGEL BROKER WARNING] Missing Angel One credentials in .env")
        return None

    try:
        totp = pyotp.TOTP(totp_key).now()
        smart_api = SmartConnect(api_key=api_key)
        session_data = smart_api.generateSession(client_code, password, totp)
        if session_data and session_data.get("status"):
            _smart_api_client = smart_api
            print("[ANGEL BROKER] Successfully authenticated with Angel One SmartAPI")
            return _smart_api_client
        else:
            print(f"[ANGEL BROKER ERROR] Authentication failed: {session_data}")
            return None
    except Exception as e:
        print(f"[ANGEL BROKER EXCEPTION] {str(e)}")
        return None

async def fetch_angel_5min_candles(symbol: str, token: str = "", lookback_days: int = 2) -> list[dict]:
    """
    Fetches 5-minute candles from Angel One SmartAPI getCandleData.
    Returns list of dicts: [{'close': float, 'volume': float, 'timestamp': str}, ...]
    """
    client = get_angel_session()
    if not client:
        return []

    now = datetime.now()
    from_date = (now - timedelta(days=lookback_days)).strftime("%Y-%m-%d 09:15")
    to_date = now.strftime("%Y-%m-%d %H:%M")

    # If token is not provided directly, symbol can be used if numeric or formatted
    symbol_token = token if token else symbol

    historic_param = {
        "exchange": "NSE",
        "symboltoken": symbol_token,
        "interval": "FIVE_MINUTE",
        "fromdate": from_date,
        "todate": to_date
    }

    try:
        res = client.getCandleData(historic_param)
        if res and res.get("status") and "data" in res and res["data"]:
            candles = []
            # Each entry in res["data"] is [timestamp, open, high, low, close, volume]
            for row in res["data"]:
                candles.append({
                    "timestamp": row[0],
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "close": float(row[4]),
                    "volume": float(row[5]),
                })
            return candles
    except Exception as e:
        print(f"[ANGEL CANDLE ERROR] Failed fetching candles for {symbol}: {str(e)}")

    return []

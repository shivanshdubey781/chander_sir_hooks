import os
import html
from datetime import datetime
import httpx
from database import get_active_watchlist, update_watchlist_state, deactivate_all_watchlist
from vwma import determine_state

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage" if BOT_TOKEN else None

async def send_telegram(text: str):
    if not TELEGRAM_API or not CHAT_ID:
        print("[MONITOR TELEGRAM SKIPPED] Bot token or chat ID missing in environment")
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                TELEGRAM_API,
                json={"chat_id": CHAT_ID.strip(), "text": text, "parse_mode": "HTML"},
            )
            resp.raise_for_status()
    except Exception as e:
        print(f"[MONITOR TELEGRAM ERROR] {str(e)}")

from angel_broker import fetch_angel_5min_candles

async def get_5min_candles(symbol: str, lookback: int = 25) -> list[dict]:
    """
    Fetch 5-minute candle data for the symbol using Angel One SmartAPI.
    Returns list of dicts: [{'close': float, 'volume': float, 'timestamp': str}, ...]
    """
    return await fetch_angel_5min_candles(symbol, lookback_days=2)


async def check_watchlist():
    """Runs every 5 minutes during market hours."""
    active_items = get_active_watchlist()
    if not active_items:
        return

    print(f"[MONITOR] Checking {len(active_items)} active watchlist items...")
    for entry in active_items:
        symbol = entry["symbol"]
        prev_state = entry["last_state"]

        try:
            candles = await get_5min_candles(symbol, lookback=25)
            if len(candles) < 20:
                continue  # Need at least 20 candles for VWMA(20)

            new_state, vwma_val, close_val = determine_state(candles, length=20)
            update_watchlist_state(symbol, new_state, vwma_val, close_val)

            # Only alert on state transitions (ignore unchanged or neutral)
            if new_state == prev_state or new_state == "neutral":
                continue

            time_str = datetime.now().strftime('%I:%M %p')
            safe_symbol = html.escape(symbol)

            if new_state == "bearish":
                await send_telegram(
                    f"⚠️ <b>Bearish VWMA Flip</b> — <b>{safe_symbol}</b>\n"
                    f"Close: ₹{close_val:.2f} | VWMA(20): ₹{vwma_val:.2f}\n"
                    f"🕒 {time_str}"
                )
            elif new_state == "bullish":
                await send_telegram(
                    f"✅ <b>Clearance Signal (Bullish)</b> — <b>{safe_symbol}</b>\n"
                    f"Close: ₹{close_val:.2f} | VWMA(20): ₹{vwma_val:.2f}\n"
                    f"🕒 {time_str}"
                )
        except Exception as e:
            print(f"[MONITOR ERROR] Error processing {symbol}: {str(e)}")

def end_of_day_reset():
    """Deactivates all active watchlist entries at end of market day (~3:35 PM IST)."""
    print("[MONITOR] Resetting active watchlist at end of day.")
    deactivate_all_watchlist()

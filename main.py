from contextlib import asynccontextmanager
import os
import html
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import httpx
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from database import init_db, save_report, get_all_reports, add_to_watchlist, get_active_watchlist
from monitor import check_watchlist, end_of_day_reset

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

load_dotenv()

scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Every 5 minutes, 9:15 AM - 3:30 PM IST, Mon-Fri
    scheduler.add_job(
        check_watchlist,
        CronTrigger(day_of_week="mon-fri", hour="9-15", minute="*/5"),
        id="check_watchlist_job",
        replace_existing=True,
    )
    # End-of-day reset at 3:35 PM IST
    scheduler.add_job(
        end_of_day_reset,
        CronTrigger(day_of_week="mon-fri", hour=15, minute=35),
        id="end_of_day_reset_job",
        replace_existing=True,
    )
    scheduler.start()
    print("[SCHEDULER] APScheduler started for Asia/Kolkata timezone")
    yield
    scheduler.shutdown()

app = FastAPI(title="Chartlink Telegram Webhook Bridge", lifespan=lifespan)
templates = Jinja2Templates(directory=TEMPLATES_DIR)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage" if BOT_TOKEN else None

@app.post("/webhook/chartlink")
async def chartlink_webhook(request: Request, key: str = ""):
    if WEBHOOK_SECRET and key != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid or missing key")

    data = {}
    try:
        data = await request.json()
    except Exception:
        try:
            form = await request.form()
            data = dict(form)
        except Exception:
            data = dict(request.query_params)

    print(f"[WEBHOOK RECEIVED] Payload: {data}")

    scan_name_raw = str(data.get("scan_name", "Chartlink Alert"))
    stocks_raw = str(data.get("stocks", ""))
    prices_raw = str(data.get("trigger_prices", ""))
    triggered_at_raw = str(data.get("triggered_at", ""))

    save_report(scan_name_raw, stocks_raw, prices_raw, triggered_at_raw)

    # Auto-add flagged symbols to stateful active watchlist for VWMA monitoring
    stock_list = [s.strip() for s in stocks_raw.split(",") if s.strip()]
    for symbol in stock_list:
        add_to_watchlist(symbol)

    scan_name = html.escape(scan_name_raw)
    triggered_at = html.escape(triggered_at_raw)
    price_list = [p.strip() for p in prices_raw.split(",") if p.strip()]
    
    lines = []
    for idx, s in enumerate(stock_list):
        p = price_list[idx] if idx < len(price_list) else "N/A"
        lines.append(f"• <b>{html.escape(s)}</b> @ ₹{html.escape(p)}")

    stock_lines = "\n".join(lines) if lines else "• No stocks listed"
    message = f"📊 <b>{scan_name}</b>\n🕒 {triggered_at}\n\n{stock_lines}"

    if TELEGRAM_API and CHAT_ID:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    TELEGRAM_API,
                    json={"chat_id": CHAT_ID.strip(), "text": message, "parse_mode": "HTML"},
                )
                print(f"[TELEGRAM API RESPONSE] Status: {resp.status_code}, Body: {resp.text}")
                if resp.status_code != 200:
                    return {"status": "ok", "warning": f"Telegram API error: {resp.text}"}
        except Exception as e:
            print(f"[TELEGRAM ERROR] {str(e)}")
            return {"status": "ok", "warning": f"Alert saved, but Telegram notification failed: {str(e)}"}
    else:
        print("[TELEGRAM SKIPPED] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing in .env")

    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    reports = get_all_reports()
    try:
        return templates.TemplateResponse(request, "index.html", {"request": request, "reports": reports})
    except TypeError:
        return templates.TemplateResponse("index.html", {"request": request, "reports": reports})

@app.get("/api/reports")
async def api_reports():
    return get_all_reports()

@app.get("/api/watchlist")
async def api_watchlist():
    return get_active_watchlist()

@app.get("/health")
async def health():
    return {"status": "alive"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=7012, reload=True)



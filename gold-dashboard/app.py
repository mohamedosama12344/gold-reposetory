import time
import threading
import requests
from flask import Flask, jsonify, render_template

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
GOLD_API_URL = "https://api.gold-api.com/price/XAU"          # free, no key, troy ounce USD
FX_API_URL = "https://open.er-api.com/v6/latest/USD"          # free, no key, USD base

GRAMS_PER_TROY_OUNCE = 31.1034768
KARATS = {
    "24K": 1.000,
    "22K": 0.9167,
    "21K": 0.875,
    "18K": 0.750,
}

TOP_CURRENCIES = ["USD", "EUR", "GBP", "SAR", "AED"]

CACHE_TTL_SECONDS = 60

_cache = {
    "data": None,
    "fetched_at": 0,
    "lock": threading.Lock(),
}


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------
def fetch_live_data():
    """Pull gold (USD/oz) + FX rates, return the combined payload the UI needs."""
    gold_resp = requests.get(GOLD_API_URL, timeout=10)
    gold_resp.raise_for_status()
    gold_usd_per_oz = float(gold_resp.json()["price"])

    fx_resp = requests.get(FX_API_URL, timeout=10)
    fx_resp.raise_for_status()
    fx_json = fx_resp.json()
    rates = fx_json["rates"]  # 1 USD = rates[CCY]

    egp_per_usd = rates["EGP"]
    gold_usd_per_gram = gold_usd_per_oz / GRAMS_PER_TROY_OUNCE
    gold_egp_per_gram = gold_usd_per_gram * egp_per_usd

    gold_by_karat = {
        karat: round(gold_egp_per_gram * factor, 2)
        for karat, factor in KARATS.items()
    }

    currencies = []
    for code in TOP_CURRENCIES:
        if code not in rates:
            continue
        # value of 1 unit of `code` expressed in EGP
        egp_value = egp_per_usd / rates[code]
        currencies.append({
            "code": code,
            "egp": round(egp_value, 4),
        })

    return {
        "gold": {
            "usd_per_ounce": round(gold_usd_per_oz, 2),
            "usd_per_gram": round(gold_usd_per_gram, 2),
            "egp_per_gram": round(gold_egp_per_gram, 2),
            "by_karat": gold_by_karat,
        },
        "currencies": currencies,
        "base_currency": "EGP",
        "updated_at": int(time.time()),
    }


def get_data(force=False):
    """Serve from cache unless it is stale or force=True. Thread-safe."""
    with _cache["lock"]:
        is_stale = (time.time() - _cache["fetched_at"]) > CACHE_TTL_SECONDS
        if force or is_stale or _cache["data"] is None:
            try:
                _cache["data"] = fetch_live_data()
                _cache["fetched_at"] = time.time()
            except Exception as exc:  # keep serving last good data if the API hiccups
                if _cache["data"] is None:
                    raise
                _cache["data"]["error"] = f"Using cached data, live fetch failed: {exc}"
        return _cache["data"]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/prices")
def api_prices():
    try:
        return jsonify(get_data())
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502


@app.route("/healthz")
def healthz():
    """Used by Jenkins / process supervisors to confirm the app is alive."""
    return jsonify({"status": "ok", "time": int(time.time())})


if __name__ == "__main__":
    # 0.0.0.0 so Jenkins-deployed instances are reachable off-box
    app.run(host="0.0.0.0", port=5000)

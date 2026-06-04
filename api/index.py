# api/index.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import json
import os

# ── 1. Create the app ─────────────────────────────────────────────────────────
app = FastAPI()

# ── 2. Enable CORS (lets dashboards from ANY website call this API) ────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Allow any website
    allow_methods=["*"],       # Allow GET, POST, OPTIONS, etc.
    allow_headers=["*"],       # Allow any headers
)

# ── 3. Load the telemetry data ONCE when the function starts ───────────────────
#    __file__ = the path to THIS file (api/index.py)
#    os.path.dirname(__file__) = the "api/" folder
#    os.path.join(...) builds the full path to the JSON file
DATA_PATH = os.path.join(os.path.dirname(__file__), "q-vercel-latency.json")
with open(DATA_PATH) as f:
    TELEMETRY = json.load(f)   # TELEMETRY is now a Python list of records

# ── 4. Define what the incoming request body looks like ───────────────────────
#    When someone POSTs {"regions": ["amer"], "threshold_ms": 180},
#    FastAPI automatically validates and parses it into this object.
class AnalyticsRequest(BaseModel):
    regions: List[str]
    threshold_ms: float

# ── 5. Helper: calculate the 95th percentile without extra packages ────────────
def p95(values: list) -> float:
    s = sorted(values)
    # Linear interpolation formula for percentile
    k = (len(s) - 1) * 0.95
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (k - lo) * (s[hi] - s[lo])

# ── 6. A simple health-check GET route ────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "Analytics API is live!"}

# ── 7. THE MAIN POST ENDPOINT ─────────────────────────────────────────────────
@app.post("/analytics")
def analytics(req: AnalyticsRequest):
    result = {}

    for region in req.regions:
        # Filter: keep only records belonging to this region
        records = [r for r in TELEMETRY if r.get("region") == region]

        if not records:
            # Return nulls if we have no data for this region
            result[region] = {
                "avg_latency": None,
                "p95_latency": None,
                "avg_uptime": None,
                "breaches": 0
            }
            continue

        # Pull out the two columns we care about
        latencies = [r["latency_ms"] for r in records]
        uptimes   = [r["uptime"]     for r in records]

        # Calculate the four required metrics
        avg_latency = sum(latencies) / len(latencies)
        p95_latency = p95(latencies)
        avg_uptime  = sum(uptimes) / len(uptimes)
        breaches    = sum(1 for l in latencies if l > req.threshold_ms)

        result[region] = {
            "avg_latency": round(avg_latency, 4),
            "p95_latency": round(p95_latency, 4),
            "avg_uptime":  round(avg_uptime, 6),
            "breaches":    breaches
        }

    return result

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import json
import numpy as np

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Force CORS headers on every response
@app.middleware("http")
async def force_cors(request, call_next):
    response = await call_next(request)

    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"

    return response


# Load telemetry JSON
DATA_FILE = Path(__file__).parent.parent / "q-vercel-latency.json"

with open(DATA_FILE, encoding="utf-8") as f:
    telemetry = json.load(f)


class RequestBody(BaseModel):
    regions: list[str]
    threshold_ms: int


# Preflight handler
@app.options("/api/latency")
def options_handler():
    response = Response(status_code=200)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response


@app.post("/api/latency")
def analytics(body: RequestBody):

    result = {}

    for region in body.regions:

        rows = [r for r in telemetry if r["region"] == region]

        latencies = [r["latency_ms"] for r in rows]
        uptimes = [r["uptime_pct"] for r in rows]

        result[region] = {
            "avg_latency": round(float(np.mean(latencies)), 2),
            "p95_latency": round(float(np.percentile(latencies, 95)), 2),
            "avg_uptime": round(float(np.mean(uptimes)), 3),
            "breaches": sum(
                1 for x in latencies
                if x > body.threshold_ms
            )
        }

    return result

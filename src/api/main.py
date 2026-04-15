"""FastAPI application entry point."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import (
    campaigns,
    ad_groups,
    keywords,
    ads,
    assets,
    bidding,
    targeting,
    batch,
)

load_dotenv()

app = FastAPI(
    title="Google Ads API — Ad Grants Campaign Manager",
    description=(
        "Programmatic management of Google Ads campaigns, ad groups, keywords, "
        "RSAs, assets, bidding strategies, and targeting. "
        "Built for Ad Grants accounts with compliance enforcement built in."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS — restrict to your Wix site origin in production ────────────────────
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "*",  # Replace with "https://yoursite.wixsite.com" for production
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
PREFIX = "/api/v1"

app.include_router(campaigns.router, prefix=PREFIX)
app.include_router(ad_groups.router, prefix=PREFIX)
app.include_router(keywords.router, prefix=PREFIX)
app.include_router(ads.router, prefix=PREFIX)
app.include_router(assets.router, prefix=PREFIX)
app.include_router(bidding.router, prefix=PREFIX)
app.include_router(targeting.router, prefix=PREFIX)
app.include_router(batch.router, prefix=PREFIX)


@app.get("/health", tags=["Health"])
@app.get("/api/v1/health", tags=["Health"])
def health_check():
    return {"status": "ok", "version": "1.0.0"}

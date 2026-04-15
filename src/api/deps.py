"""FastAPI dependency injection — API key auth, client, and per-service factories."""

from __future__ import annotations

import os
from functools import lru_cache

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from src.auth.client import get_client
from src.services.campaign_service import CampaignService
from src.services.ad_group_service import AdGroupService
from src.services.keyword_service import KeywordService
from src.services.rsa_service import RSAService
from src.services.asset_service import AssetService
from src.services.bidding_service import BiddingService
from src.services.targeting_service import TargetingService
from src.services.batch_service import BatchService

_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def _get_expected_key() -> str:
    key = os.getenv("API_SECRET_KEY", "")
    if not key:
        raise RuntimeError("API_SECRET_KEY environment variable is not set.")
    return key


def verify_api_key(api_key: str | None = Security(_API_KEY_HEADER)) -> None:
    """Reject requests that don't supply the correct X-API-Key header."""
    if api_key != _get_expected_key():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )


# ── Service factories ─────────────────────────────────────────────────────────
# Each factory creates a fresh service instance bound to the shared client.

def get_campaign_service() -> CampaignService:
    return CampaignService(get_client())


def get_ad_group_service() -> AdGroupService:
    return AdGroupService(get_client())


def get_keyword_service() -> KeywordService:
    return KeywordService(get_client())


def get_rsa_service() -> RSAService:
    return RSAService(get_client())


def get_asset_service() -> AssetService:
    return AssetService(get_client())


def get_bidding_service() -> BiddingService:
    return BiddingService(get_client())


def get_targeting_service() -> TargetingService:
    return TargetingService(get_client())


def get_batch_service() -> BatchService:
    return BatchService(get_client())

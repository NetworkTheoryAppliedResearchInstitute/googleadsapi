from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class BiddingStrategyType(str, Enum):
    MAXIMIZE_CLICKS = "MAXIMIZE_CLICKS"
    MAXIMIZE_CONVERSIONS = "MAXIMIZE_CONVERSIONS"
    TARGET_CPA = "TARGET_CPA"
    TARGET_ROAS = "TARGET_ROAS"
    TARGET_IMPRESSION_SHARE = "TARGET_IMPRESSION_SHARE"
    TARGET_SPEND = "TARGET_SPEND"


class ImpressionShareLocation(str, Enum):
    ANYWHERE = "ANYWHERE"
    TOP_OF_PAGE = "TOP_OF_PAGE"
    ABSOLUTE_TOP_OF_PAGE = "ABSOLUTE_TOP_OF_PAGE"


class CreatePortfolioBiddingStrategyRequest(BaseModel):
    """Creates a shared (portfolio) bidding strategy reusable across campaigns."""

    name: str = Field(..., min_length=1)
    strategy_type: BiddingStrategyType

    # Target CPA
    target_cpa_micros: Optional[int] = None

    # Target ROAS
    target_roas: Optional[float] = None

    # Target Impression Share
    target_impression_share_location: Optional[ImpressionShareLocation] = None
    target_impression_share_fraction: Optional[float] = Field(
        None, ge=0.0, le=1.0
    )

    # Maximize Clicks / Target Spend — optional cpc ceiling
    cpc_bid_ceiling_micros: Optional[int] = None

    # Maximize Conversions / Maximize Clicks — optional spend target
    target_spend_micros: Optional[int] = None

    # Smart Bidding Exploration (v21+): wider ROAS tolerance range
    target_roas_min: Optional[float] = None
    target_roas_max: Optional[float] = None


class BiddingStrategyResponse(BaseModel):
    resource_name: str
    strategy_id: str
    name: str
    strategy_type: str

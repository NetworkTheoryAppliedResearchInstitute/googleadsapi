from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class CampaignType(str, Enum):
    SEARCH = "SEARCH"
    DISPLAY = "DISPLAY"
    PERFORMANCE_MAX = "PERFORMANCE_MAX"
    SHOPPING = "SHOPPING"
    VIDEO = "VIDEO"
    DEMAND_GEN = "DEMAND_GEN"
    APP = "APP"
    SMART = "SMART"
    LOCAL_SERVICES = "LOCAL_SERVICES"


class CampaignStatus(str, Enum):
    ENABLED = "ENABLED"
    PAUSED = "PAUSED"
    REMOVED = "REMOVED"


class BiddingStrategyType(str, Enum):
    MANUAL_CPC = "MANUAL_CPC"
    ENHANCED_CPC = "ENHANCED_CPC"
    MAXIMIZE_CLICKS = "MAXIMIZE_CLICKS"
    MAXIMIZE_CONVERSIONS = "MAXIMIZE_CONVERSIONS"
    TARGET_CPA = "TARGET_CPA"
    TARGET_ROAS = "TARGET_ROAS"
    TARGET_IMPRESSION_SHARE = "TARGET_IMPRESSION_SHARE"
    PORTFOLIO = "PORTFOLIO"  # reference an existing portfolio strategy by ID


class ImpressionShareLocation(str, Enum):
    ANYWHERE = "ANYWHERE"
    TOP_OF_PAGE = "TOP_OF_PAGE"
    ABSOLUTE_TOP_OF_PAGE = "ABSOLUTE_TOP_OF_PAGE"


class NetworkSettings(BaseModel):
    target_google_search: bool = True
    target_search_network: bool = True
    target_content_network: bool = False
    target_partner_search_network: bool = False


class CreateCampaignRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    campaign_type: CampaignType = CampaignType.SEARCH
    status: CampaignStatus = CampaignStatus.PAUSED

    # Budget — supply either a new daily budget amount or a shared budget resource name
    daily_budget_micros: Optional[int] = Field(
        None, description="Daily budget in micros. 1 USD = 1,000,000 micros."
    )
    shared_budget_resource_name: Optional[str] = None

    # Bidding
    bidding_strategy_type: BiddingStrategyType = BiddingStrategyType.MANUAL_CPC
    portfolio_bidding_strategy_id: Optional[str] = None  # used when type=PORTFOLIO
    enhanced_cpc_enabled: bool = False

    # Target CPA
    target_cpa_micros: Optional[int] = None

    # Target ROAS
    target_roas: Optional[float] = None

    # Target Impression Share
    target_impression_share_location: Optional[ImpressionShareLocation] = None
    target_impression_share_fraction: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="0.0–1.0"
    )
    cpc_bid_ceiling_micros: Optional[int] = None

    # Network settings
    network_settings: NetworkSettings = Field(default_factory=NetworkSettings)

    # Geo/language (GeoTargetConstant resource IDs and LanguageConstant resource IDs)
    geo_target_constant_ids: list[int] = Field(default_factory=list)
    language_constant_ids: list[int] = Field(default_factory=list)

    # Schedule
    start_date: Optional[str] = Field(
        None, description="YYYYMMDD format. Defaults to today."
    )
    end_date: Optional[str] = Field(None, description="YYYYMMDD format.")

    # Ad Grants compliance flag — enforces $2 CPC cap if True
    ad_grants_account: bool = False

    @field_validator("daily_budget_micros", mode="before")
    @classmethod
    def require_budget(cls, v, info):
        # Allow None if shared_budget_resource_name will be supplied (cross-field)
        return v


class UpdateCampaignRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[CampaignStatus] = None
    daily_budget_micros: Optional[int] = None
    bidding_strategy_type: Optional[BiddingStrategyType] = None
    target_cpa_micros: Optional[int] = None
    target_roas: Optional[float] = None
    cpc_bid_ceiling_micros: Optional[int] = None
    network_settings: Optional[NetworkSettings] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class CampaignResponse(BaseModel):
    resource_name: str
    campaign_id: str
    name: str
    status: str
    campaign_type: str
    budget_resource_name: Optional[str] = None

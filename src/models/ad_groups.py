from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AdGroupType(str, Enum):
    SEARCH_STANDARD = "SEARCH_STANDARD"
    DISPLAY_STANDARD = "DISPLAY_STANDARD"
    SHOPPING_PRODUCT_ADS = "SHOPPING_PRODUCT_ADS"
    VIDEO_BUMPER = "VIDEO_BUMPER"
    VIDEO_TRUE_VIEW_IN_STREAM = "VIDEO_TRUE_VIEW_IN_STREAM"


class AdGroupStatus(str, Enum):
    ENABLED = "ENABLED"
    PAUSED = "PAUSED"
    REMOVED = "REMOVED"


class CreateAdGroupRequest(BaseModel):
    campaign_id: str = Field(..., description="ID of the parent campaign.")
    name: str = Field(..., min_length=1, max_length=255)
    ad_group_type: AdGroupType = AdGroupType.SEARCH_STANDARD
    status: AdGroupStatus = AdGroupStatus.ENABLED
    cpc_bid_micros: Optional[int] = Field(
        None,
        description="Default CPC bid in micros. For Ad Grants, max 2,000,000 (= $2.00).",
    )

    # Ad group–level targeting overrides
    geo_target_constant_ids: list[int] = Field(default_factory=list)
    language_constant_ids: list[int] = Field(default_factory=list)


class UpdateAdGroupRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[AdGroupStatus] = None
    cpc_bid_micros: Optional[int] = None


class AdGroupResponse(BaseModel):
    resource_name: str
    ad_group_id: str
    name: str
    status: str
    ad_group_type: str
    campaign_id: str
    cpc_bid_micros: Optional[int] = None

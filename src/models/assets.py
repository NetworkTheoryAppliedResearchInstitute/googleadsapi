from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AssetType(str, Enum):
    SITELINK = "SITELINK"
    CALLOUT = "CALLOUT"
    STRUCTURED_SNIPPET = "STRUCTURED_SNIPPET"
    CALL = "CALL"
    PRICE = "PRICE"
    PROMOTION = "PROMOTION"
    IMAGE = "IMAGE"
    LEAD_FORM = "LEAD_FORM"
    BUSINESS_MESSAGE = "BUSINESS_MESSAGE"


class AssetFieldType(str, Enum):
    """Where an asset is linked (slot in the ad)."""
    SITELINK = "SITELINK"
    CALLOUT = "CALLOUT"
    STRUCTURED_SNIPPET = "STRUCTURED_SNIPPET"
    CALL = "CALL"
    PRICE = "PRICE"
    PROMOTION = "PROMOTION"
    AD_IMAGE = "AD_IMAGE"
    LEAD_FORM = "LEAD_FORM"
    BUSINESS_MESSAGE = "BUSINESS_MESSAGE"


class AssetLinkLevel(str, Enum):
    CUSTOMER = "CUSTOMER"
    CAMPAIGN = "CAMPAIGN"
    AD_GROUP = "AD_GROUP"


# ── Individual asset payloads ────────────────────────────────────────────────

class SitelinkAsset(BaseModel):
    link_text: str = Field(..., max_length=25)
    description1: Optional[str] = Field(None, max_length=35)
    description2: Optional[str] = Field(None, max_length=35)
    final_urls: list[str] = Field(..., min_length=1)
    final_mobile_urls: list[str] = Field(default_factory=list)


class CalloutAsset(BaseModel):
    callout_text: str = Field(..., max_length=25)


class StructuredSnippetAsset(BaseModel):
    header: str = Field(..., description="Snippet header (e.g. 'Services', 'Brands').")
    values: list[str] = Field(..., min_length=3, max_length=10)


class CallAsset(BaseModel):
    phone_number: str
    country_code: str = Field(..., max_length=2, description="ISO 3166-1 alpha-2.")
    call_conversion_reporting_state: Optional[str] = Field(
        "USE_ACCOUNT_LEVEL_CALL_CONVERSION_ACTION",
        description="USE_ACCOUNT_LEVEL_CALL_CONVERSION_ACTION | USE_RESOURCE_LEVEL_CALL_CONVERSION_ACTION",
    )


class PriceItem(BaseModel):
    header: str = Field(..., max_length=25)
    description: str = Field(..., max_length=25)
    price_micros: int
    currency_code: str = Field("USD", max_length=3)
    unit: Optional[str] = None  # e.g. "PER_MONTH"
    final_urls: list[str] = Field(..., min_length=1)


class PriceAsset(BaseModel):
    type: str = Field("SERVICES", description="Price feed type, e.g. SERVICES, PRODUCTS.")
    price_qualifier: Optional[str] = None  # STARTING_FROM | UP_TO | AVERAGE
    language_code: str = "EN"
    items: list[PriceItem] = Field(..., min_length=3, max_length=8)


class PromotionAsset(BaseModel):
    promotion_target: str = Field(..., max_length=20)
    discount_modifier: Optional[str] = None  # UP_TO
    percent_off: Optional[int] = Field(None, ge=1, le=100)
    money_off_amount_micros: Optional[int] = None
    currency_code: str = "USD"
    occasion: Optional[str] = None  # e.g. NEW_YEARS, CHRISTMAS
    final_urls: list[str] = Field(..., min_length=1)
    start_date: Optional[str] = None  # YYYY-MM-DD
    end_date: Optional[str] = None


class ImageAsset(BaseModel):
    """Supply either a public URL or base64-encoded image data."""
    image_url: Optional[str] = None
    image_data_base64: Optional[str] = None
    mime_type: str = "IMAGE_JPEG"


class LeadFormAsset(BaseModel):
    business_name: str
    headline: str = Field(..., max_length=30)
    description: str = Field(..., max_length=200)
    privacy_policy_url: str
    post_submit_headline: Optional[str] = Field(None, max_length=30)
    post_submit_description: Optional[str] = Field(None, max_length=200)
    background_image_url: Optional[str] = None


# ── Create & Link requests ───────────────────────────────────────────────────

class CreateAssetRequest(BaseModel):
    asset_type: AssetType
    # Populate exactly the sub-model that matches asset_type
    sitelink: Optional[SitelinkAsset] = None
    callout: Optional[CalloutAsset] = None
    structured_snippet: Optional[StructuredSnippetAsset] = None
    call: Optional[CallAsset] = None
    price: Optional[PriceAsset] = None
    promotion: Optional[PromotionAsset] = None
    image: Optional[ImageAsset] = None
    lead_form: Optional[LeadFormAsset] = None


class LinkAssetRequest(BaseModel):
    asset_resource_name: str
    field_type: AssetFieldType
    link_level: AssetLinkLevel = AssetLinkLevel.CAMPAIGN
    # Provide the relevant ID for the chosen link level:
    campaign_id: Optional[str] = None
    ad_group_id: Optional[str] = None

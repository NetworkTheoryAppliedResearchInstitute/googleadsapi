from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class KeywordMatchType(str, Enum):
    BROAD = "BROAD"
    PHRASE = "PHRASE"
    EXACT = "EXACT"


class KeywordStatus(str, Enum):
    ENABLED = "ENABLED"
    PAUSED = "PAUSED"
    REMOVED = "REMOVED"


class CreateKeywordRequest(BaseModel):
    ad_group_id: str
    keyword_text: str = Field(..., min_length=1)
    match_type: KeywordMatchType = KeywordMatchType.BROAD
    cpc_bid_micros: Optional[int] = Field(
        None,
        description="Keyword-level CPC bid override in micros. Ad Grants max: 2,000,000.",
    )
    status: KeywordStatus = KeywordStatus.ENABLED
    final_urls: list[str] = Field(default_factory=list)


class CreateNegativeKeywordRequest(BaseModel):
    keyword_text: str = Field(..., min_length=1)
    match_type: KeywordMatchType = KeywordMatchType.PHRASE
    # Supply exactly one of the two targets:
    campaign_id: Optional[str] = None
    ad_group_id: Optional[str] = None


class UpdateKeywordBidRequest(BaseModel):
    ad_group_id: str
    criterion_id: str
    cpc_bid_micros: int
    match_type: Optional[KeywordMatchType] = None
    status: Optional[KeywordStatus] = None


class KeywordResponse(BaseModel):
    resource_name: str
    criterion_id: str
    ad_group_id: str
    keyword_text: str
    match_type: str
    status: str
    cpc_bid_micros: Optional[int] = None
    quality_score: Optional[int] = None


class SharedNegativeListRequest(BaseModel):
    """Create a shared negative keyword list and optionally attach it to campaigns."""

    list_name: str
    keywords: list[CreateNegativeKeywordRequest]
    campaign_ids: list[str] = Field(
        default_factory=list,
        description="Campaigns to attach this shared list to immediately.",
    )


class BulkCreateKeywordsRequest(BaseModel):
    keywords: list[CreateKeywordRequest]
    use_batch_job: bool = Field(
        True,
        description="Use BatchJobService for large sets (>500 keywords). Recommended.",
    )

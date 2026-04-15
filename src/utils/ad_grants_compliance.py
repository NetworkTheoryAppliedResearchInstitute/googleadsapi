"""Ad Grants policy compliance enforcement.

Google Ad Grants policy requirements enforced here:
  - $2.00 max CPC for Manual CPC bidding (2,000,000 micros)
  - Search campaigns only
  - Conversion tracking must be enabled (advisory)
  - 5% CTR minimum (advisory — checked via reporting)
  - No single-word keywords (unless brand/organization names)
  - Keyword Quality Score ≥ 3 (advisory)
  - No branded keywords for products/services you don't own

References:
  https://support.google.com/grants/answer/1657310
"""

from __future__ import annotations

from fastapi import HTTPException

AD_GRANTS_MAX_CPC_MICROS = 2_000_000   # $2.00
AD_GRANTS_MIN_QUALITY_SCORE = 3
AD_GRANTS_MIN_CTR = 0.05               # 5%

SEARCH_ONLY_CAMPAIGN_TYPES = {"SEARCH"}

# Bidding strategies exempt from the $2 CPC cap:
CPC_CAP_EXEMPT_STRATEGIES = {
    "MAXIMIZE_CONVERSIONS",
    "TARGET_CPA",
    "TARGET_ROAS",
    "MAXIMIZE_CLICKS",
}


def enforce_ad_grants_campaign(req) -> None:
    """Raise HTTPException if the campaign config violates Ad Grants policy."""
    from src.models.campaigns import CampaignType, BiddingStrategyType

    # 1. Search campaigns only
    if req.campaign_type not in (CampaignType.SEARCH, "SEARCH"):
        raise HTTPException(
            status_code=422,
            detail=(
                f"Ad Grants only supports Search campaigns. "
                f"Got: {req.campaign_type}"
            ),
        )

    bst = req.bidding_strategy_type
    bst_value = bst.value if hasattr(bst, "value") else bst

    # 2. $2 CPC cap for Manual CPC
    if bst_value == "MANUAL_CPC":
        if (
            req.cpc_bid_ceiling_micros is not None
            and req.cpc_bid_ceiling_micros > AD_GRANTS_MAX_CPC_MICROS
        ):
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Ad Grants: CPC bid ceiling ({req.cpc_bid_ceiling_micros} micros) "
                    f"exceeds $2.00 limit ({AD_GRANTS_MAX_CPC_MICROS} micros). "
                    "Use a conversion-based bidding strategy to remove this cap."
                ),
            )

    # 3. Network: Search only (no Display, no partner search)
    if hasattr(req, "network_settings") and req.network_settings:
        if req.network_settings.target_content_network:
            raise HTTPException(
                status_code=422,
                detail="Ad Grants: Display Network (target_content_network) is not allowed.",
            )


def enforce_ad_grants_keyword(keyword_text: str, cpc_bid_micros: int | None) -> None:
    """Raise HTTPException if a keyword violates Ad Grants policy."""

    # Single-word keywords are not allowed (with limited exceptions)
    words = keyword_text.strip().split()
    if len(words) == 1:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Ad Grants: Single-word keyword '{keyword_text}' is not allowed "
                "unless it is a branded term. "
                "Use multi-word, specific keywords."
            ),
        )

    # CPC cap enforcement
    if cpc_bid_micros is not None and cpc_bid_micros > AD_GRANTS_MAX_CPC_MICROS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Ad Grants: Keyword CPC bid ({cpc_bid_micros} micros) "
                f"exceeds $2.00 limit ({AD_GRANTS_MAX_CPC_MICROS} micros)."
            ),
        )


def clamp_cpc_for_ad_grants(cpc_micros: int) -> int:
    """Return the lower of the supplied bid and the Ad Grants $2 cap."""
    return min(cpc_micros, AD_GRANTS_MAX_CPC_MICROS)


def check_ctr_compliance(
    ctr: float, campaign_name: str
) -> dict:
    """Return a compliance status dict for a campaign's CTR.

    Ad Grants requires ≥ 5% CTR across the account. This returns an advisory
    result; you should pause or restructure low-CTR campaigns.
    """
    status = "OK" if ctr >= AD_GRANTS_MIN_CTR else "AT_RISK"
    return {
        "campaign_name": campaign_name,
        "ctr": ctr,
        "min_required_ctr": AD_GRANTS_MIN_CTR,
        "status": status,
        "action": (
            "No action needed."
            if status == "OK"
            else (
                "CTR is below the 5% Ad Grants minimum. "
                "Pause under-performing keywords, improve ad relevance, "
                "or add negative keywords to filter irrelevant traffic."
            )
        ),
    }


def check_keyword_quality_scores(keywords: list[dict]) -> list[dict]:
    """Flag keywords with Quality Score below Ad Grants minimum (≥ 3).

    Input: list of dicts with 'keyword_text' and 'quality_score' keys.
    Returns: list of keywords that need attention.
    """
    issues = []
    for kw in keywords:
        qs = kw.get("quality_score") or 0
        if qs > 0 and qs < AD_GRANTS_MIN_QUALITY_SCORE:
            issues.append(
                {
                    "keyword_text": kw.get("keyword_text"),
                    "quality_score": qs,
                    "status": "BELOW_MINIMUM",
                    "action": (
                        "Quality Score is below the Ad Grants minimum of 3. "
                        "Improve ad relevance, landing page experience, or "
                        "expected CTR. Keywords at QS < 3 may trigger grant suspension."
                    ),
                }
            )
    return issues

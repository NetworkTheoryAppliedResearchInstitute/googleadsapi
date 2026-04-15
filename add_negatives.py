"""
add_negatives.py — NTARI P2-002 Section 3.3
============================================================
Creates a shared negative keyword list ("NTARI P2-002 Account Negatives")
and attaches it to all 8 English broadcast campaigns.

Run once before enabling any campaign:
    python add_negatives.py
"""

from __future__ import annotations

import os
import sys
from dotenv import load_dotenv

load_dotenv()

# ── Load google-ads.yaml from the project root ────────────────────────────────
YAML_PATH = os.path.join(os.path.dirname(__file__), "google-ads.yaml")
CUSTOMER_ID = os.getenv("GOOGLE_ADS_CUSTOMER_ID", "").replace("-", "")

# ── P2-002 Section 3.3 — Account-level negative keywords ─────────────────────
NEGATIVE_KEYWORDS: list[str] = [
    # Commercial intent
    "buy", "price", "cost", "discount", "sale", "cheap", "purchase",
    "order", "shop", "deal", "promo", "hire", "salary",
    # Employment
    "jobs", "careers", "employment", "resume", "apply", "recruiter",
    "job listing", "intern", "internship",
    # Unrelated consumer
    "gaming", "sports", "entertainment", "movies", "music", "dating",
    "recipes", "fashion", "travel deals",
    # Paid certifications
    "certification cost", "exam fee", "certificate price",
    "paid online course", "udemy", "coursera",
    # News / current events
    "news", "breaking", "latest", "today", "yesterday", "scandal", "trending",
    # Medical / legal services
    "lawyer", "attorney", "doctor", "hospital", "medication",
    "legal advice", "therapy",
]

# ── Campaigns built by execute_plan.py ───────────────────────────────────────
CAMPAIGN_NAMES = [
    "EN_DigitalCommons_Search",
    "EN_SOHO_Search",
    "EN_Economics_Search",
    "EN_Anthropology_Search",
    "EN_Statecraft_Search",
    "EN_KnowledgeCommons_Search",
    "EN_Projects_Search",
    "EN_Branded_Navigation",
]

SHARED_SET_NAME = "NTARI P2-002 Account Negatives"


def get_existing_shared_set(client, customer_id: str) -> str | None:
    """Return resource name of existing shared set, or None if not found."""
    ga_svc = client.get_service("GoogleAdsService")
    query = f"""
        SELECT shared_set.name, shared_set.resource_name
        FROM shared_set
        WHERE shared_set.name = '{SHARED_SET_NAME}'
          AND shared_set.status = 'ENABLED'
    """
    for row in ga_svc.search(customer_id=customer_id, query=query):
        return row.shared_set.resource_name
    return None


def get_campaign_resource_names(client, customer_id: str) -> dict[str, str]:
    """Return {campaign_name: resource_name} for all NTARI campaigns."""
    ga_svc = client.get_service("GoogleAdsService")
    # Query ALL campaigns so we can show what actually exists if names don't match
    query = """
        SELECT campaign.name, campaign.resource_name, campaign.status
        FROM campaign
        ORDER BY campaign.name
    """
    all_campaigns = {}
    for row in ga_svc.search(customer_id=customer_id, query=query):
        all_campaigns[row.campaign.name] = row.campaign.resource_name

    # Match against our expected names
    results = {n: all_campaigns[n] for n in CAMPAIGN_NAMES if n in all_campaigns}

    # If nothing matched, print what IS in the account to help diagnose
    if not results:
        print()
        print("      DEBUG — campaigns found in account:")
        for name in sorted(all_campaigns):
            print(f"        • {name}")
        print()

    return results


def create_shared_set(client, customer_id: str) -> str:
    """Create the shared negative keyword list, return resource name."""
    svc = client.get_service("SharedSetService")
    op = client.get_type("SharedSetOperation")
    shared_set = op.create
    shared_set.name = SHARED_SET_NAME
    shared_set.type_ = client.enums.SharedSetTypeEnum.NEGATIVE_KEYWORDS
    resp = svc.mutate_shared_sets(customer_id=customer_id, operations=[op])
    rn = resp.results[0].resource_name
    print(f"  Created shared set: {rn}")
    return rn


def add_keywords_to_shared_set(client, customer_id: str, shared_set_rn: str) -> int:
    """Add all negative keywords to the shared set. Returns count added."""
    svc = client.get_service("SharedCriterionService")
    operations = []
    for kw in NEGATIVE_KEYWORDS:
        op = client.get_type("SharedCriterionOperation")
        criterion = op.create
        criterion.shared_set = shared_set_rn
        criterion.keyword.text = kw
        criterion.keyword.match_type = client.enums.KeywordMatchTypeEnum.BROAD
        operations.append(op)

    # Batch in chunks of 1000 (API limit per mutate call)
    added = 0
    for i in range(0, len(operations), 1000):
        chunk = operations[i : i + 1000]
        svc.mutate_shared_criteria(customer_id=customer_id, operations=chunk)
        added += len(chunk)
    return added


def attach_to_campaigns(
    client,
    customer_id: str,
    shared_set_rn: str,
    campaign_resource_names: dict[str, str],
) -> int:
    """Link the shared set to every campaign. Returns count linked."""
    svc = client.get_service("CampaignSharedSetService")
    operations = []
    for name, campaign_rn in campaign_resource_names.items():
        op = client.get_type("CampaignSharedSetOperation")
        css = op.create
        css.campaign = campaign_rn
        css.shared_set = shared_set_rn
        operations.append(op)

    resp = svc.mutate_campaign_shared_sets(
        customer_id=customer_id, operations=operations
    )
    return len(resp.results)


def main() -> None:
    from google.ads.googleads.client import GoogleAdsClient

    if not CUSTOMER_ID:
        print("ERROR  GOOGLE_ADS_CUSTOMER_ID not set in .env")
        sys.exit(1)

    print()
    print("=" * 60)
    print("  NTARI P2-002 — Section 3.3 Account Negative Keywords")
    print("=" * 60)
    print(f"  Customer ID : {CUSTOMER_ID}")
    print(f"  Keywords    : {len(NEGATIVE_KEYWORDS)}")
    print(f"  Campaigns   : {len(CAMPAIGN_NAMES)}")
    print()

    client = GoogleAdsClient.load_from_storage(path=YAML_PATH, version="v20")

    # 1 — Look up campaign resource names
    print("[1/3] Looking up campaign resource names...")
    campaign_rns = get_campaign_resource_names(client, CUSTOMER_ID)
    found = [n for n in CAMPAIGN_NAMES if n in campaign_rns]
    missing = [n for n in CAMPAIGN_NAMES if n not in campaign_rns]
    print(f"      Found {len(found)}/{len(CAMPAIGN_NAMES)} campaigns")
    if missing:
        print(f"      WARN  Not found (will be skipped): {missing}")

    # 2 — Reuse or create shared negative keyword list
    print(f"[2/3] Checking for existing shared set: '{SHARED_SET_NAME}'...")
    shared_set_rn = get_existing_shared_set(client, CUSTOMER_ID)
    if shared_set_rn:
        print(f"      Reusing existing shared set: {shared_set_rn}")
    else:
        shared_set_rn = create_shared_set(client, CUSTOMER_ID)
        kw_count = add_keywords_to_shared_set(client, CUSTOMER_ID, shared_set_rn)
        print(f"      Added {kw_count} negative keywords")

    # 3 — Attach to all campaigns
    if not campaign_rns:
        print("[3/3] SKIP — no matching campaigns found (see DEBUG output above)")
        print()
        print("  ACTION REQUIRED: Check the campaign names above and update")
        print("  CAMPAIGN_NAMES in add_negatives.py to match exactly, then re-run.")
        return

    print("[3/3] Attaching to campaigns...")
    linked = attach_to_campaigns(client, CUSTOMER_ID, shared_set_rn, campaign_rns)
    print(f"      Linked to {linked} campaigns")

    print()
    print("=" * 60)
    print("  DONE — Negative keyword list active on all campaigns.")
    print("  View in Google Ads: Tools → Shared Library → Negative keyword lists")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
